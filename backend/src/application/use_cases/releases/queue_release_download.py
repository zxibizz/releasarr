"""Queue release downloads for media requests."""

from __future__ import annotations

from loguru import logger

from src.application.interfaces.media_requests import MediaRequestRepository
from src.application.interfaces.releases import (
    CreateReleaseData,
    ReleaseDownloadService,
    ReleaseRepository,
    ReleaseSearchService,
)
from src.application.use_cases.releases.auto_mapping import ReleaseAutoMapper
from src.application.use_cases.releases.commands import QueueReleaseDownloadCommand
from src.application.use_cases.releases.dto import AsyncOperationDTO
from src.application.use_cases.releases.exceptions import (
    ReleaseDownloadConflictError,
    ReleaseDownloadFailedError,
    ReleaseNotFoundError,
)
from src.application.use_cases.releases.grab import ReleaseGrabFinalizer, to_release_files
from src.application.use_cases.releases.mappers import queued_download_to_async_operation
from src.application.utility.torrent import TorrentInfo, parse_torrent


class QueueReleaseDownloadUseCase:
    """Use case enqueuing release downloads via the download client."""

    def __init__(
        self,
        repository: ReleaseRepository,
        download_service: ReleaseDownloadService,
        search_service: ReleaseSearchService,
        request_repository: MediaRequestRepository | None = None,
        auto_mapper: ReleaseAutoMapper | None = None,
    ) -> None:
        self._repository = repository
        self._download_service = download_service
        self._search_service = search_service
        self._finalizer = ReleaseGrabFinalizer(request_repository, auto_mapper)

    async def execute(self, command: QueueReleaseDownloadCommand) -> AsyncOperationDTO:
        # Anything that goes wrong below has to be logged against the request
        # before it propagates. A caller only sees the resulting error response,
        # while the request's activity view is built from log records filtered on
        # request_id, so an unlogged failure leaves no trace of the attempt.
        effective_request_id = command.request_id
        try:
            release = await self._repository.get_release(command.release_id)
            if release is not None:
                raise ReleaseDownloadConflictError(command.request_id, command.release_id)

            candidate = self._search_service.resolve(command.release_id)
            if candidate is None:
                raise ReleaseNotFoundError(command.release_id)

            effective_request_id = candidate.request_id or command.request_id
            if not effective_request_id:
                raise ReleaseDownloadConflictError(command.request_id, command.release_id)

            magnet_link = candidate.magnet_link
            torrent_bytes: bytes | None = None
            torrent: TorrentInfo | None = None

            if candidate.torrent_file_url:
                try:
                    torrent_bytes = await self._search_service.fetch_torrent(
                        candidate.torrent_file_url
                    )
                    torrent = parse_torrent(torrent_bytes)
                    magnet_link = torrent.magnet_link
                except Exception as exc:  # pragma: no cover - fallback to magnet when parsing fails
                    logger.warning(
                        "Failed to resolve torrent file, falling back to magnet link",
                        request_id=effective_request_id,
                        release_id=command.release_id,
                        error=str(exc),
                    )
                    torrent_bytes = None
                    torrent = None

            if not magnet_link:
                raise ReleaseNotFoundError(command.release_id)

            try:
                queued = await self._download_service.queue_download(
                    effective_request_id,
                    command.release_id,
                    magnet_link,
                    torrent_bytes,
                )
            except Exception as exc:  # pragma: no cover - defensive
                raise ReleaseDownloadFailedError(command.release_id, str(exc)) from exc

            try:
                release = await self._repository.create_release(
                    data=CreateReleaseData(
                        magnet_link=magnet_link,
                        request_ids=[effective_request_id],
                        id=candidate.release_id,
                        name=candidate.release_name,
                        source=candidate.source or "",
                        quality=candidate.quality or "",
                        files=to_release_files(torrent.files) if torrent else None,
                    )
                )
            except ValueError as exc:
                raise ReleaseDownloadConflictError(command.request_id, command.release_id) from exc
        except Exception as exc:
            logger.opt(exception=exc).error(
                f"Failed to grab release: {exc}",
                request_id=effective_request_id,
                release_id=command.release_id,
                error=str(exc),
            )
            raise

        logger.info(
            f"Grabbed release {candidate.release_name}",
            request_id=effective_request_id,
            release_id=command.release_id,
            release_name=candidate.release_name,
            source=candidate.source,
            quality=candidate.quality,
        )
        await self._finalizer.mark_request_downloading(effective_request_id)
        await self._finalizer.auto_map_files(release)

        return queued_download_to_async_operation(queued)


__all__ = ["QueueReleaseDownloadUseCase"]
