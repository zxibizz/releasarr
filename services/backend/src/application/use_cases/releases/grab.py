"""Steps shared by every path that grabs a release."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import uuid4

from loguru import logger

from src.application.interfaces.media_requests import (
    MediaRequestRepository,
    UpdateMediaRequestData,
)
from src.application.interfaces.releases import ReleaseFileRecord, ReleaseRecord
from src.application.use_cases.releases.auto_mapping import ReleaseAutoMapper
from src.application.utility.torrent import TorrentFileInfo
from src.domain.enums import MediaRequestStatus


def to_release_files(files: Sequence[TorrentFileInfo]) -> list[ReleaseFileRecord]:
    """Turn a torrent's file list into unmapped release file records."""

    return [
        ReleaseFileRecord(
            id=str(uuid4()),
            name=file.name,
            size_bytes=file.size_bytes,
            path=file.name,
            mapping=None,
        )
        for file in files
    ]


class ReleaseGrabFinalizer:
    """Bookkeeping that follows a queued grab.

    The torrent is already with the download client and the release already
    stored by the time any of this runs, so a failure here must not surface.
    """

    def __init__(
        self,
        request_repository: MediaRequestRepository | None = None,
        auto_mapper: ReleaseAutoMapper | None = None,
    ) -> None:
        self._request_repository = request_repository
        self._auto_mapper = auto_mapper

    async def mark_request_downloading(self, request_id: str) -> None:
        """Reflect the grab on the request straight away.

        The release sync is what keeps request status honest from here on; this
        only avoids leaving the request on ``pending`` until the next cycle.
        """
        if self._request_repository is None:
            return
        try:
            await self._request_repository.update_request(
                request_id,
                UpdateMediaRequestData(status=MediaRequestStatus.DOWNLOADING),
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "Failed to mark request as downloading",
                request_id=request_id,
                error=str(exc),
            )

    async def auto_map_files(self, release: ReleaseRecord) -> None:
        """Map the files the torrent metadata revealed.

        A grab that only resolved to a magnet link carries no file list, leaving
        nothing to map.
        """
        if self._auto_mapper is None or not release.files:
            return
        try:
            await self._auto_mapper.apply(release)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "Failed to auto-map release files",
                release_id=release.id,
                error=str(exc),
            )


__all__ = ["ReleaseGrabFinalizer", "to_release_files"]
