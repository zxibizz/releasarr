"""Queue release downloads for media requests."""

from __future__ import annotations

from urllib.parse import quote_plus
from uuid import uuid4

from loguru import logger
from torrentool.api import Torrent

from src.application.interfaces.media_requests import (
    MediaRequestRepository,
    UpdateMediaRequestData,
)
from src.application.interfaces.releases import (
    CreateReleaseData,
    ReleaseDownloadService,
    ReleaseFileRecord,
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
from src.domain.enums import MediaRequestStatus


class QueueReleaseDownloadUseCase:
    """Use case enqueuing release downloads via the download client."""

    def __init__(
        self,
        repository: ReleaseRepository,
        download_service: ReleaseDownloadService,
        search_service: ReleaseSearchService,
        request_repository: MediaRequestRepository | None = None,
    ) -> None:
        self._repository = repository
        self._download_service = download_service
        self._search_service = search_service
        self._request_repository = request_repository

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
                torrent_bytes = await self._search_service.fetch_torrent(candidate.torrent_file_url)
                torrent = Torrent.from_string(torrent_bytes)
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
        else:
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
                    files=self._extract_files(torrent) if torrent else None,
                )
            )
        except ValueError as exc:
            raise ReleaseDownloadConflictError(command.request_id, command.release_id) from exc

        logger.info(
            f"Grabbed release {candidate.release_name}",
            request_id=effective_request_id,
            release_id=command.release_id,
            release_name=candidate.release_name,
            source=candidate.source,
            quality=candidate.quality,
        )
        await self._mark_request_downloading(effective_request_id)

        return queued_download_to_async_operation(queued)

    async def _mark_request_downloading(self, request_id: str) -> None:
        """Reflect the grab on the request straight away.

        The release sync is what keeps request status honest from here on; this only
        avoids leaving the request on ``pending`` until the next sync cycle. The
        torrent is already queued at this point, so a failure here must not surface.
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

    def _magnet_from_release(self, release: ReleaseRecord) -> str:
        quoted_name = quote_plus(release.name) if release.name else None
        magnet = f"magnet:?xt=urn:btih:{release.info_hash}"
        if quoted_name:
            magnet = f"{magnet}&dn={quoted_name}"
        return magnet

    def _extract_files(self, torrent: Torrent) -> list[ReleaseFileRecord]:
        files: list[ReleaseFileRecord] = []
        for file in torrent.files:
            files.append(
                ReleaseFileRecord(
                    id=str(uuid4()),
                    name=file.name,
                    size_bytes=file.length,
                    path=file.name,  # Simple path for now
                    mapping=None,
                )
            )
        return files


__all__ = ["QueueReleaseDownloadUseCase"]
