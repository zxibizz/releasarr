"""Use case for re-grabbing releases that have been updated on the indexer."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

from loguru._logger import Logger
from torrentool.api import Torrent

from src.application.interfaces.indexers import IndexerDirectory, IndexerRecord
from src.application.interfaces.releases import (
    ReleaseDownloadService,
    ReleaseRepository,
    ReleaseSearchService,
    ReleaseSearchUnavailableError,
)
from src.application.interfaces.request_warnings import (
    RequestWarningRecord,
    RequestWarningRepository,
)
from src.application.use_cases.indexers.list_indexers import derive_health
from src.core.logging import get_logger
from src.domain.enums import IndexerHealth, RequestWarningCode


class RegrabOutdatedReleasesUseCase:
    """Check for updates to existing releases (e.g. repacks) and re-download them."""

    def __init__(
        self,
        repository: ReleaseRepository,
        search_service: ReleaseSearchService,
        download_service: ReleaseDownloadService,
        directory: IndexerDirectory | None = None,
        warning_repository: RequestWarningRepository | None = None,
        logger: Logger | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._search_service = search_service
        self._download_service = download_service
        self._directory = directory
        self._warning_repository = warning_repository
        self._logger = logger or get_logger(component="regrab_outdated_releases")
        self._clock = clock or (lambda: datetime.now(UTC))

    async def execute(self) -> None:
        """Process potential outdated releases."""
        releases = await self._repository.get_potential_outdated_releases()
        indexers_by_name = await self._indexers_by_name()

        for release in releases:
            try:
                await self._process_release(release, indexers_by_name)
            except Exception as exc:
                # Bound per request id so a failed re-grab is visible on the
                # request left holding the stale release, not just in the
                # scheduler's own log.
                for request_id in release.request_ids or ["unknown"]:
                    self._logger.opt(exception=exc).error(
                        f"Failed to re-grab release: {exc}",
                        request_id=request_id,
                        release_id=release.id,
                        release_name=release.name,
                        error=str(exc),
                    )

    async def _indexers_by_name(self) -> dict[str, IndexerRecord]:
        """Map a release's stored indexer name back to Prowlarr's own record.

        Best-effort: a release older than the indexer list, or Prowlarr being
        briefly unreachable, should not stop every regrab check from running -
        it just falls back to the unscoped search for that release.
        """

        if self._directory is None:
            return {}
        try:
            indexers = await self._directory.list_indexers()
        except Exception as exc:
            self._logger.warning("Failed to list indexers for regrab scoping", error=str(exc))
            return {}
        return {indexer.name.lower(): indexer for indexer in indexers}

    async def _process_release(self, release, indexers_by_name: dict[str, IndexerRecord]) -> None:
        # Search Prowlarr for the specific release, scoped to the indexer it
        # originally came from when that indexer is still known to Prowlarr.
        # We rely on the release name (torrent name) to find it again.
        indexer = (
            indexers_by_name.get(release.torrent_source.lower()) if release.torrent_source else None
        )

        if indexer is not None and derive_health(indexer, self._clock()) is IndexerHealth.BLOCKED:
            # Prowlarr is already backing this indexer off: querying it anyway
            # would just eat the timeout budget on a search it will refuse, the
            # same reasoning the fan-out search applies before ever calling out.
            reason = f"indexer {indexer.name} blocked by Prowlarr until {indexer.disabled_till}"
            for request_id in release.request_ids or ["unknown"]:
                self._logger.warning(
                    "Could not check for updates: indexer blocked by Prowlarr",
                    request_id=request_id,
                    release_id=release.id,
                    release_name=release.name,
                    disabled_till=indexer.disabled_till,
                )
            await self._write_regrab_warning(release, reason=reason)
            return

        indexer_id = indexer.indexer_id if indexer is not None else None
        try:
            results = await self._search_service.search(release.name, indexer_id=indexer_id)
        except ReleaseSearchUnavailableError as exc:
            # An indexer that is banned or not responding is an expected, transient
            # condition rather than a bug, but the request it would have updated is
            # left stale, which is worth surfacing on that request's activity log.
            for request_id in release.request_ids or ["unknown"]:
                self._logger.warning(
                    "Could not check for updates: indexer unavailable",
                    request_id=request_id,
                    release_id=release.id,
                    release_name=release.name,
                    error=str(exc),
                )
            await self._write_regrab_warning(release, reason=str(exc))
            return

        await self._write_regrab_warning(release, reason=None)

        # Find the result that matches our current GUID (Release.id)
        match = next((r for r in results.results if r.release_id == release.id), None)
        if not match:
            # Maybe removed from indexer or name changed significantly?
            return

        new_hash: str | None = None
        torrent_bytes: bytes | None = None

        # distinct source logic
        if match.magnet_link:
            new_hash = self._extract_hash_from_magnet(match.magnet_link)

        if not new_hash and match.torrent_file_url:
            try:
                torrent_bytes = await self._search_service.fetch_torrent(match.torrent_file_url)
                t = Torrent.from_string(torrent_bytes)
                new_hash = t.info_hash
            except Exception as exc:
                self._logger.warning("Failed to fetch/parse torrent file", error=str(exc))

        if not new_hash:
            return

        # Compare hashes (case insensitive)
        current_hash = release.info_hash
        if new_hash.upper() != current_hash.upper():
            request_ids = release.request_ids or ["unknown"]

            await self._download_service.queue_download(
                request_id=request_ids[0],
                release_id=release.id,
                magnet_link=match.magnet_link or "",
                torrent_bytes=torrent_bytes,
            )

            # Update DB
            await self._repository.update_release(
                release.id,
                info_hash=new_hash.upper(),
                export_failures_count=0,
                last_exported_info_hash=None,  # Reset export
                name=match.release_name,  # Update name in case of rename
                info_url=match.info_url,
                published_at=match.publish_date,
            )

            for request_id in request_ids:
                self._logger.info(
                    f"Re-grabbed updated release {match.release_name}",
                    request_id=request_id,
                    release_id=release.id,
                    release_name=match.release_name,
                    old_hash=current_hash,
                    new_hash=new_hash.upper(),
                )

    async def _write_regrab_warning(self, release, reason: str | None) -> None:
        """Record or clear `REGRAB_INDEXER_UNAVAILABLE` for this release alone.

        Scoped to the release, not the request: a request with several
        releases must not have a sibling's fresh failure wiped out just
        because this release's own check came back clean.
        """

        if self._warning_repository is None:
            return
        rows = (
            []
            if reason is None
            else [
                RequestWarningRecord(
                    request_id=request_id,
                    release_id=release.id,
                    code=RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE,
                    details={"reason": reason},
                )
                for request_id in release.request_ids
            ]
        )
        try:
            await self._warning_repository.replace_for_releases(
                RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE, [release.id], rows
            )
        except Exception as exc:  # pragma: no cover - defensive
            self._logger.warning(
                "Failed to persist regrab indexer-unavailable warning",
                release_id=release.id,
                error=str(exc),
            )

    @staticmethod
    def _extract_hash_from_magnet(magnet_link: str) -> str | None:
        try:
            parsed = urlparse(magnet_link)
            if parsed.scheme != "magnet":
                return None
            params = parse_qs(parsed.query)
            xt_values = params.get("xt", [])
            for value in xt_values:
                if value.startswith("urn:btih:"):
                    return value.split(":")[-1].upper()
        except Exception:
            return None
        return None
