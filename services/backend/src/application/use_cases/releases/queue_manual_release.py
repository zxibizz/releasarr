"""Queue releases the user supplied by hand rather than picked from a search."""

from __future__ import annotations

from loguru import logger

from src.application.interfaces.media_requests import MediaRequestRepository
from src.application.interfaces.releases import (
    CreateReleaseData,
    ReleaseDownloadService,
    ReleaseFileRecord,
    ReleaseRepository,
)
from src.application.use_cases.releases.auto_mapping import ReleaseAutoMapper
from src.application.use_cases.releases.commands import QueueManualReleaseCommand
from src.application.use_cases.releases.dto import AsyncOperationDTO
from src.application.use_cases.releases.exceptions import (
    ReleaseDownloadConflictError,
    ReleaseDownloadFailedError,
)
from src.application.use_cases.releases.grab import ReleaseGrabFinalizer, to_release_files
from src.application.use_cases.releases.mappers import queued_download_to_async_operation
from src.application.utility.magnet import parse_magnet
from src.application.utility.torrent import decode_torrent_base64, parse_torrent

MANUAL_SOURCE = "manual"


class QueueManualReleaseUseCase:
    """Use case enqueuing a torrent file or magnet link against a request.

    Unlike the search-driven grab there is no indexer candidate to resolve, so
    the release identity comes from the torrent metadata itself.
    """

    def __init__(
        self,
        repository: ReleaseRepository,
        download_service: ReleaseDownloadService,
        request_repository: MediaRequestRepository | None = None,
        auto_mapper: ReleaseAutoMapper | None = None,
    ) -> None:
        self._repository = repository
        self._download_service = download_service
        self._finalizer = ReleaseGrabFinalizer(request_repository, auto_mapper)

    async def execute(self, command: QueueManualReleaseCommand) -> AsyncOperationDTO:
        if not command.request_id:
            raise ValueError("request_id must be supplied")

        torrent_base64 = (command.torrent_file_base64 or "").strip()
        magnet_input = (command.magnet_link or "").strip()
        if bool(torrent_base64) == bool(magnet_input):
            raise ValueError("supply exactly one of torrent_file_base64 or magnet_link")

        torrent_bytes: bytes | None = None
        files: list[ReleaseFileRecord] | None = None

        if torrent_base64:
            torrent_bytes = decode_torrent_base64(torrent_base64)
            torrent = parse_torrent(torrent_bytes)
            magnet_link = torrent.magnet_link
            name = torrent.name
            files = to_release_files(torrent.files)
        else:
            magnet_link = magnet_input
            name = ""

        # A magnet carries the info hash outright, and the one torrentool derives
        # from a parsed file arrives the same way, so both identify the release
        # the way ``CreateReleaseUseCase`` already does.
        magnet = parse_magnet(magnet_link)
        release_id = magnet.info_hash
        name = name or magnet.display_name

        if await self._repository.get_release(release_id) is not None:
            raise ReleaseDownloadConflictError(command.request_id, release_id)

        try:
            queued = await self._download_service.queue_download(
                command.request_id,
                release_id,
                magnet_link,
                torrent_bytes,
            )
        except Exception as exc:
            raise ReleaseDownloadFailedError(release_id, str(exc)) from exc

        try:
            release = await self._repository.create_release(
                data=CreateReleaseData(
                    magnet_link=magnet_link,
                    request_ids=[command.request_id],
                    id=release_id,
                    name=name,
                    source=MANUAL_SOURCE,
                    quality="",
                    files=files,
                )
            )
        except ValueError as exc:
            raise ReleaseDownloadConflictError(command.request_id, release_id) from exc

        logger.info(
            f"Grabbed release {name} manually",
            request_id=command.request_id,
            release_id=release_id,
            release_name=name,
            source=MANUAL_SOURCE,
            ingest_source="torrent_file" if torrent_bytes else "magnet",
        )
        await self._finalizer.mark_request_downloading(command.request_id)
        await self._finalizer.auto_map_files(release)

        return queued_download_to_async_operation(queued)


__all__ = ["QueueManualReleaseUseCase"]
