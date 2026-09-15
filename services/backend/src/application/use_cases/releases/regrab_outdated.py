"""Use case for re-grabbing releases that have been updated on the indexer."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from loguru._logger import Logger
from torrentool.api import Torrent

from src.application.interfaces.indexers import IndexerDirectory
from src.application.interfaces.releases import (
    ReleaseDownloadService,
    ReleaseRepository,
    ReleaseSearchService,
)
from src.core.logging import get_logger


class RegrabOutdatedReleasesUseCase:
    """Check for updates to existing releases (e.g. repacks) and re-download them."""

    def __init__(
        self,
        repository: ReleaseRepository,
        search_service: ReleaseSearchService,
        download_service: ReleaseDownloadService,
        directory: IndexerDirectory | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._repository = repository
        self._search_service = search_service
        self._download_service = download_service
        self._directory = directory
        self._logger = logger or get_logger(component="regrab_outdated_releases")

    async def execute(self) -> None:
        """Process potential outdated releases."""
        releases = await self._repository.get_potential_outdated_releases()
        indexer_ids_by_name = await self._indexer_ids_by_name()

        for release in releases:
            try:
                await self._process_release(release, indexer_ids_by_name)
            except Exception as exc:
                self._logger.opt(exception=exc).error(
                    "Failed to check for updates",
                    release_id=release.id,
                    release_name=release.name,
                    error=str(exc),
                )

    async def _indexer_ids_by_name(self) -> dict[str, int]:
        """Map a release's stored indexer name back to Prowlarr's own id.

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
        return {indexer.name.lower(): indexer.indexer_id for indexer in indexers}

    async def _process_release(self, release, indexer_ids_by_name: dict[str, int]) -> None:
        # Search Prowlarr for the specific release, scoped to the indexer it
        # originally came from when that indexer is still known to Prowlarr.
        # We rely on the release name (torrent name) to find it again.
        indexer_id = (
            indexer_ids_by_name.get(release.torrent_source.lower())
            if release.torrent_source
            else None
        )
        results = await self._search_service.search(release.name, indexer_id=indexer_id)

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
            self._logger.info(
                "Found updated release",
                release_name=release.name,
                old_hash=current_hash,
                new_hash=new_hash,
            )

            # Re-download
            request_id = release.request_ids[0] if release.request_ids else "unknown"

            await self._download_service.queue_download(
                request_id=request_id,
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
