"""Queue release downloads for media requests."""

from __future__ import annotations

from src.application.interfaces.releases import ReleaseDownloadService, ReleaseRepository
from src.application.use_cases.releases.commands import QueueReleaseDownloadCommand
from src.application.use_cases.releases.dto import AsyncOperationDTO
from src.application.use_cases.releases.exceptions import (
    ReleaseDownloadConflictError,
    ReleaseNotFoundError,
)
from src.application.use_cases.releases.mappers import queued_download_to_async_operation


class QueueReleaseDownloadUseCase:
    """Use case enqueuing release downloads via the download client."""

    def __init__(
        self,
        repository: ReleaseRepository,
        download_service: ReleaseDownloadService,
    ) -> None:
        self._repository = repository
        self._download_service = download_service

    async def execute(self, command: QueueReleaseDownloadCommand) -> AsyncOperationDTO:
        release = await self._repository.get_release(command.release_id)
        if release is None:
            raise ReleaseNotFoundError(command.release_id)

        if command.request_id not in release.request_ids:
            raise ReleaseDownloadConflictError(command.request_id, command.release_id)

        queued = await self._download_service.queue_download(command.request_id, command.release_id)
        return queued_download_to_async_operation(queued)


__all__ = ["QueueReleaseDownloadUseCase"]
