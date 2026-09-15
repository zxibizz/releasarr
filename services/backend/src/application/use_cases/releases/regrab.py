"""Checking a release against its indexer, and re-downloading it when it moved.

Shared by the scheduled re-grab sweep and the on-demand refresh on a request, so
the two cannot drift on what counts as outdated, on the warnings they leave
behind, or on what they log against the request.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

from torrentool.api import Torrent

from src.application.interfaces.indexers import IndexerDirectory, IndexerRecord
from src.application.interfaces.releases import (
    MANUAL_SOURCE,
    ReleaseDownloadService,
    ReleaseRecord,
    ReleaseRepository,
    ReleaseSearchService,
    ReleaseSearchUnavailableError,
)
from src.application.interfaces.request_warnings import (
    RequestWarningRecord,
    RequestWarningRepository,
)
from src.application.use_cases.indexers.list_indexers import derive_health
from src.application.use_cases.requests.recompute_state import RecomputeRequestStateUseCase
from src.core.logging import get_logger
from src.domain.enums import IndexerHealth, ReleaseStatus, RequestWarningCode

if TYPE_CHECKING:
    from loguru import Logger


def is_regrabbable(release: ReleaseRecord) -> bool:
    """Whether an indexer can still be asked about this release.

    A hand-supplied torrent has no indexer to go back to and can never be found
    again, which is why the sweep filters those out in SQL as well.
    """

    return release.torrent_source is not None and release.torrent_source != MANUAL_SOURCE


class ReleaseRegrapper:
    """Looks releases up again on their own indexer and re-downloads replaced torrents.

    The check is a search for the release's own name, scoped to the indexer it
    came from, followed by a comparison of info hashes: an indexer that replaced
    a torrent (a repack) serves the same release id under a new hash.
    """

    def __init__(
        self,
        repository: ReleaseRepository,
        search_service: ReleaseSearchService,
        download_service: ReleaseDownloadService,
        warning_repository: RequestWarningRepository,
        recompute_state: RecomputeRequestStateUseCase,
        directory: IndexerDirectory,
        logger: Logger | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._search_service = search_service
        self._download_service = download_service
        self._directory = directory
        self._warning_repository = warning_repository
        self._recompute_state = recompute_state
        self._logger = logger or get_logger(component="regrab_releases")
        self._clock = clock or (lambda: datetime.now(UTC))

    async def indexers_by_name(self) -> dict[str, IndexerRecord]:
        """Map a release's stored indexer name back to Prowlarr's own record.

        Best-effort: a release older than the indexer list, or Prowlarr being
        briefly unreachable, should not stop every re-grab check from running -
        it just falls back to the unscoped search for that release.
        """

        if not self._directory.is_configured:
            return {}
        try:
            indexers = await self._directory.list_indexers()
        except Exception as exc:
            self._logger.warning("Failed to list indexers for regrab scoping", error=str(exc))
            return {}
        return {indexer.name.lower(): indexer for indexer in indexers}

    def _log_for_requests(
        self,
        log: Callable[..., None],
        message: str,
        release: ReleaseRecord,
        **fields: object,
    ) -> None:
        """Record one line per request holding this release.

        A request's activity view is built by filtering the log file on
        `request_id`, so a line that names only the release is reachable from the
        logs page but invisible on every request it belongs to. A release shared
        by several requests is why this is a loop rather than one call.
        """

        for request_id in release.request_ids or ["unknown"]:
            log(message, request_id=request_id, release_id=release.id, **fields)

    async def regrab(
        self, release: ReleaseRecord, indexers_by_name: dict[str, IndexerRecord]
    ) -> bool:
        """Check one release, re-downloading it when the indexer replaced it.

        Returns whether a new download was queued. Every way out of here logs
        against the release's requests: a check that found nothing to do is still
        the answer to "what happened to this request", and the sweep runs hourly
        over releases nobody is watching.
        """

        # Search Prowlarr for the specific release, scoped to the indexer it
        # originally came from when that indexer is still known to Prowlarr.
        # We rely on the release name (torrent name) to find it again.
        indexer = (
            indexers_by_name.get(release.torrent_source.lower()) if release.torrent_source else None
        )

        unusable = self._unusable_reason(indexer)
        if unusable is not None:
            # Prowlarr will refuse the query either way, so spending the timeout
            # budget on it only delays the rest of the sweep.
            self._log_for_requests(
                self._logger.warning,
                "Could not check for updates: indexer unusable",
                release,
                release_name=release.name,
                indexer=release.torrent_source,
                reason=unusable,
            )
            await self._write_regrab_warning(release, reason=unusable)
            return False

        indexer_id = indexer.indexer_id if indexer is not None else None
        try:
            results = await self._search_service.search(release.name, indexer_id=indexer_id)
        except ReleaseSearchUnavailableError as exc:
            # An indexer that is banned or not responding is an expected, transient
            # condition rather than a bug, but the request it would have updated is
            # left stale, which is worth surfacing on that request's activity log.
            self._log_for_requests(
                self._logger.warning,
                "Could not check for updates: indexer unavailable",
                release,
                release_name=release.name,
                error=str(exc),
            )
            await self._write_regrab_warning(release, reason=str(exc))
            return False

        await self._write_regrab_warning(release, reason=None)

        # Find the result that matches our current GUID (Release.id)
        match = next((r for r in results.results if r.release_id == release.id), None)
        if not match:
            # The indexer dropped the release or reissued it under another id, so
            # there is no torrent left to compare hashes against.
            self._log_for_requests(
                self._logger.info,
                "Release is no longer listed by its indexer",
                release,
                release_name=release.name,
                indexer=release.torrent_source,
            )
            await self._write_not_listed_warning(release, indexer=release.torrent_source)
            return False

        # The release is still listed, so a row an earlier check left behind is
        # cleared here rather than on any valid response: an indexer that
        # answered without knowing this release is exactly what set it.
        await self._write_not_listed_warning(release, indexer=None)

        new_hash: str | None = None
        torrent_bytes: bytes | None = None

        # distinct source logic
        if match.magnet_link:
            new_hash = self._extract_hash_from_magnet(match.magnet_link)

        if not new_hash and match.torrent_file_url:
            try:
                torrent_bytes = await self._search_service.fetch_torrent(match.torrent_file_url)
                torrent = Torrent.from_string(torrent_bytes)
                new_hash = torrent.info_hash
            except Exception as exc:
                self._log_for_requests(
                    self._logger.warning,
                    "Failed to fetch/parse torrent file",
                    release,
                    release_name=release.name,
                    error=str(exc),
                )
                return False

        if not new_hash:
            # Neither link the indexer reported yielded a hash, so there is nothing
            # to compare against and the release cannot be called outdated.
            self._log_for_requests(
                self._logger.warning,
                "Could not read the release's info hash",
                release,
                release_name=release.name,
                indexer=release.torrent_source,
            )
            return False

        # Compare hashes (case insensitive)
        current_hash = release.info_hash
        if new_hash.upper() == current_hash.upper():
            self._log_for_requests(
                self._logger.info,
                "Release is up to date on its indexer",
                release,
                release_name=release.name,
                indexer=release.torrent_source,
                info_hash=current_hash,
            )
            return False

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
            # The replacement is the same release downloaded again, so the row
            # cannot go on calling itself finished: `completed` is what the export
            # queue imports from, and the files are being replaced underneath it.
            # Reading the client back is what settles the real status, so this is
            # only the state the queued download starts in.
            status=ReleaseStatus.DOWNLOADING,
            progress=0.0,
            completed_at=None,
        )

        self._log_for_requests(
            self._logger.info,
            "Re-grabbed updated release",
            release,
            release_name=match.release_name,
            indexer=release.torrent_source,
            old_hash=current_hash,
            new_hash=new_hash.upper(),
        )

        try:
            # The new torrent is back in flight and `published_at` just
            # moved, so the request must leave `monitoring` immediately
            # rather than wait for the next release sync.
            await self._recompute_state.execute(request_ids)
        except Exception as exc:  # pragma: no cover - defensive
            self._log_for_requests(
                self._logger.warning,
                "Failed to settle requests after a re-grab",
                release,
                error=str(exc),
            )

        return True

    def _unusable_reason(self, indexer: IndexerRecord | None) -> str | None:
        """Why this indexer cannot answer a search right now, or None if it can.

        An unknown indexer is not reported: the search falls back to Prowlarr's
        unscoped sweep, which may still find the release elsewhere.
        """

        if indexer is None:
            return None
        health = derive_health(indexer, self._clock())
        if health is IndexerHealth.DISABLED:
            return f"indexer {indexer.name} is disabled in Prowlarr"
        if health is IndexerHealth.BLOCKED:
            return f"indexer {indexer.name} is blocked by Prowlarr until {indexer.disabled_till}"
        if not indexer.supports_search:
            return f"indexer {indexer.name} does not support search"
        return None

    async def _write_regrab_warning(self, release: ReleaseRecord, reason: str | None) -> None:
        """Record or clear `REGRAB_INDEXER_UNAVAILABLE` for this release alone.

        Scoped to the release, not the request: a request with several
        releases must not have a sibling's fresh failure wiped out just
        because this release's own check came back clean.
        """

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
            self._log_for_requests(
                self._logger.warning,
                "Failed to persist regrab indexer-unavailable warning",
                release,
                error=str(exc),
            )

    async def _write_not_listed_warning(self, release: ReleaseRecord, indexer: str | None) -> None:
        """Record or clear `RELEASE_NOT_LISTED` for this release alone.

        Overloading `indexer` with None to mean "clear" mirrors
        `_write_regrab_warning`, and is only safe because the two callers sit on
        either side of the match test: the release is guaranteed to carry a
        `torrent_source`, since releases without one are never checked.

        The code is deliberately not cleared on every valid search response the
        way `REGRAB_INDEXER_UNAVAILABLE` is: an indexer answering without this
        release is precisely the condition, so only finding it again resolves
        it.
        """

        rows = (
            []
            if indexer is None
            else [
                RequestWarningRecord(
                    request_id=request_id,
                    release_id=release.id,
                    code=RequestWarningCode.RELEASE_NOT_LISTED,
                    details={"indexer": indexer},
                )
                for request_id in release.request_ids
            ]
        )
        try:
            await self._warning_repository.replace_for_releases(
                RequestWarningCode.RELEASE_NOT_LISTED, [release.id], rows
            )
        except Exception as exc:  # pragma: no cover - defensive
            self._log_for_requests(
                self._logger.warning,
                "Failed to persist release-not-listed warning",
                release,
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


__all__ = ["ReleaseRegrapper", "is_regrabbable"]
