"""Steps shared by every path that grabs a release."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import uuid4

from loguru import logger

from src.application.interfaces.releases import ReleaseFileRecord, ReleaseRecord
from src.application.use_cases.releases.auto_mapping import ReleaseAutoMapper
from src.application.use_cases.requests.recompute_state import RecomputeRequestStateUseCase
from src.application.utility.torrent import TorrentFileInfo


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
        auto_mapper: ReleaseAutoMapper | None = None,
        recompute_state: RecomputeRequestStateUseCase | None = None,
    ) -> None:
        self._auto_mapper = auto_mapper
        self._recompute_state = recompute_state

    async def finalize(self, release: ReleaseRecord) -> None:
        """Map the files the torrent metadata revealed, then settle the request.

        Runs after every grab, magnet-only or not: a release with no file list
        still has to pull its request out of ``pending``.
        """
        if self._auto_mapper is not None and release.files:
            try:
                await self._auto_mapper.apply(release)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(
                    "Failed to auto-map release files",
                    release_id=release.id,
                    error=str(exc),
                )

        if self._recompute_state is None:
            return
        try:
            await self._recompute_state.execute(release.request_ids)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "Failed to recompute request state",
                release_id=release.id,
                error=str(exc),
            )


__all__ = ["ReleaseGrabFinalizer", "to_release_files"]
