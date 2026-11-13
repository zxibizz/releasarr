"""Hand a search result's .torrent file to the caller."""

from __future__ import annotations

import re

from loguru._logger import Logger

from src.application.interfaces.releases import ReleaseSearchService, TorrentFetchError
from src.application.use_cases.indexers.exceptions import ProwlarrNotConfiguredError
from src.application.use_cases.releases.dto import SearchTorrentDTO
from src.application.use_cases.releases.exceptions import (
    ReleaseNotFoundError,
    ReleaseTorrentUnavailableError,
)
from src.application.utility.torrent import parse_torrent
from src.core.logging import get_logger
from src.domain.enums import LogComponent

# Characters no common filesystem takes in a name, plus control characters that
# would let a release title break out of a Content-Disposition header.
_UNSAFE_FILENAME_CHARS = re.compile(r'[\x00-\x1f\x7f/\\:*?"<>|]+')
_MAX_FILENAME_STEM = 200


def _filename(name: str) -> str:
    stem = _UNSAFE_FILENAME_CHARS.sub("_", name).strip(" ._")[:_MAX_FILENAME_STEM].strip()
    return f"{stem or 'release'}.torrent"


class DownloadSearchTorrentUseCase:
    """Fetch a search result's .torrent through Prowlarr on the caller's behalf.

    Prowlarr's download link carries its API key, so the caller is never given
    it. The link is resolved here from a result this process returned, never
    taken from the caller, which keeps this from fetching anything Prowlarr did
    not offer.
    """

    def __init__(self, search_service: ReleaseSearchService, logger: Logger | None = None) -> None:
        self._search_service = search_service
        self._logger = logger or get_logger(LogComponent.USECASE_RELEASE_SEARCH)

    async def execute(self, release_id: str) -> SearchTorrentDTO:
        if not self._search_service.is_configured:
            raise ProwlarrNotConfiguredError

        candidate = self._search_service.resolve(release_id)
        if candidate is None:
            raise ReleaseNotFoundError(release_id)
        if not candidate.torrent_file_url:
            raise ReleaseTorrentUnavailableError(release_id)

        try:
            content = await self._search_service.fetch_torrent(candidate.torrent_file_url)
            # Checked so that whatever else Prowlarr might answer with - an
            # indexer's HTML error page, say - is not passed on as a torrent.
            torrent = parse_torrent(content)
        except (TorrentFetchError, ValueError) as exc:
            self._logger.warning(
                "Could not fetch a search result's torrent file",
                release_id=release_id,
                source=candidate.source,
                error=str(exc),
            )
            if isinstance(exc, TorrentFetchError):
                raise
            raise TorrentFetchError("Prowlarr did not return a readable torrent file") from exc

        return SearchTorrentDTO(
            filename=_filename(torrent.name or candidate.release_name), content=content
        )


__all__ = ["DownloadSearchTorrentUseCase"]
