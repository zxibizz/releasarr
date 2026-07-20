"""Queue release downloads for media requests."""

from __future__ import annotations

from urllib.parse import quote_plus

from loguru import logger
from torrentool.api import Torrent

from src.application.interfaces.releases import (
    CreateReleaseData,
    ReleaseDownloadService,
    ReleaseRecord,
    ReleaseRepository,
    ReleaseSearchService,
)
from src.application.use_cases.releases.commands import QueueReleaseDownloadCommand
from src.application.use_cases.releases.dto import AsyncOperationDTO
from src.application.use_cases.releases.exceptions import (
    ReleaseDownloadConflictError,
    ReleaseDownloadFailedError,
    ReleaseNotFoundError,
)
from src.application.use_cases.releases.mappers import queued_download_to_async_operation


class QueueReleaseDownloadUseCase:
    """Use case enqueuing release downloads via the download client."""

    def __init__(
        self,
        repository: ReleaseRepository,
        download_service: ReleaseDownloadService,
        search_service: ReleaseSearchService,
    ) -> None:
        self._repository = repository
        self._download_service = download_service
        self._search_service = search_service

    async def execute(self, command: QueueReleaseDownloadCommand) -> AsyncOperationDTO:
        release = await self._repository.get_release(command.release_id)
        effective_request_id = command.request_id
        magnet_link: str | None = None
        torrent_bytes: bytes | None = None

        if release is not None:
            raise ReleaseDownloadConflictError(command.request_id, command.release_id)  

        candidate = self._search_service.resolve(command.release_id)
        if candidate is None:
            raise ReleaseNotFoundError(command.release_id)

        effective_request_id = candidate.request_id or command.request_id
        if not effective_request_id:
            raise ReleaseDownloadConflictError(command.request_id, command.release_id)

        magnet_link = candidate.magnet_link

        if candidate.torrent_file_url:
            try:
                torrent_bytes = await self._search_service.fetch_torrent(
                    candidate.torrent_file_url
                )
                torrent = Torrent.from_string(torrent_bytes)
                magnet_link = torrent.magnet_link
            except Exception as exc:  # pragma: no cover - fallback to magnet when parsing fails
                logger.warning(
                    "Failed to resolve torrent file for release candidate",
                    release_id=command.release_id,
                    error=str(exc),
                )
                torrent_bytes = None

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
                    source=candidate.source,
                    quality=candidate.quality,
                )
            )
        except ValueError as exc:
            raise ReleaseDownloadConflictError(
                command.request_id, command.release_id
            ) from exc

        return queued_download_to_async_operation(queued)

    def _magnet_from_release(self, release: ReleaseRecord) -> str:
        quoted_name = quote_plus(release.name) if release.name else None
        magnet = f"magnet:?xt=urn:btih:{release.info_hash}"
        if quoted_name:
            magnet = f"{magnet}&dn={quoted_name}"
        return magnet


__all__ = ["QueueReleaseDownloadUseCase"]
