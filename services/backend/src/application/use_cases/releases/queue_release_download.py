"""Queue release downloads for media requests."""

from __future__ import annotations

from src.application.interfaces.releases import (
    CreateReleaseData,
    ReleaseDownloadService,
    ReleaseRecord,
    ReleaseRepository,
    ReleaseSearchService,
)
from src.application.use_cases.indexers.exceptions import ProwlarrNotConfiguredError
from src.application.use_cases.releases.auto_mapping import ReleaseAutoMapper
from src.application.use_cases.releases.commands import QueueReleaseDownloadCommand
from src.application.use_cases.releases.dto import AsyncOperationDTO
from src.application.use_cases.releases.exceptions import (
    ExistingReleasesDecisionRequiredError,
    QbittorrentNotConfiguredError,
    ReleaseDownloadConflictError,
    ReleaseDownloadFailedError,
    ReleaseNotFoundError,
)
from src.application.use_cases.releases.grab import ReleaseGrabFinalizer, to_release_files
from src.application.use_cases.releases.mappers import queued_download_to_async_operation
from src.application.use_cases.releases.replace_existing import ExistingReleaseReplacer
from src.application.use_cases.requests.recompute_state import RecomputeRequestStateUseCase
from src.application.utility.torrent import TorrentInfo, parse_torrent
from src.core.logging import get_logger
from src.domain.enums import ExistingReleasesAction, LogComponent

_logger = get_logger(LogComponent.USECASE_QUEUE_DOWNLOAD)


class QueueReleaseDownloadUseCase:
    """Use case enqueuing release downloads via the download client."""

    def __init__(
        self,
        repository: ReleaseRepository,
        download_service: ReleaseDownloadService,
        search_service: ReleaseSearchService,
        auto_mapper: ReleaseAutoMapper,
        existing_release_replacer: ExistingReleaseReplacer,
        recompute_state: RecomputeRequestStateUseCase,
    ) -> None:
        self._repository = repository
        self._download_service = download_service
        self._search_service = search_service
        self._finalizer = ReleaseGrabFinalizer(auto_mapper, recompute_state)
        self._existing_release_replacer = existing_release_replacer

    async def _existing_releases(self, request_id: str) -> list[ReleaseRecord]:
        return await self._existing_release_replacer.existing_for(request_id)

    async def execute(self, command: QueueReleaseDownloadCommand) -> AsyncOperationDTO:
        # Anything that goes wrong below has to be logged against the request
        # before it propagates. A caller only sees the resulting error response,
        # while the request's activity view is built from log records filtered on
        # request_id, so an unlogged failure leaves no trace of the attempt.
        effective_request_id = command.request_id
        try:
            # The two providers are what the grab is made of: a candidate comes
            # from the search, the torrent goes to the client. Checked here so the
            # failure is logged against the request like any other.
            if not self._search_service.is_configured:
                raise ProwlarrNotConfiguredError
            if not self._download_service.is_configured:
                raise QbittorrentNotConfiguredError

            release = await self._repository.get_release(command.release_id)
            if release is not None:
                raise ReleaseDownloadConflictError(command.request_id, command.release_id)

            candidate = self._search_service.resolve(command.release_id)
            if candidate is None:
                raise ReleaseNotFoundError(command.release_id)

            effective_request_id = candidate.request_id or command.request_id
            if not effective_request_id:
                raise ReleaseDownloadConflictError(command.request_id, command.release_id)

            # A new grab must not silently pile onto whatever this request already
            # has queued or seeding; the caller has to say what to do about it.
            existing_releases = await self._existing_releases(effective_request_id)
            if existing_releases and command.existing_releases is None:
                raise ExistingReleasesDecisionRequiredError(
                    effective_request_id, [release.id for release in existing_releases]
                )

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
                    _logger.warning(
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
                        info_url=candidate.info_url,
                        published_at=candidate.publish_date,
                        # Kept because the regrab check has to search this release
                        # again, and its own name is the tracker's title - not
                        # what the tracker's search was asked for.
                        search_query=(candidate.query or "").strip() or None,
                    )
                )
            except ValueError as exc:
                raise ReleaseDownloadConflictError(command.request_id, command.release_id) from exc
        except Exception as exc:
            _logger.opt(exception=exc).error(
                f"Failed to grab release: {exc}",
                request_id=effective_request_id,
                release_id=command.release_id,
                error=str(exc),
            )
            raise

        _logger.info(
            f"Grabbed release {candidate.release_name}",
            request_id=effective_request_id,
            release_id=command.release_id,
            release_name=candidate.release_name,
            source=candidate.source,
            quality=candidate.quality,
        )
        await self._finalizer.finalize(release)

        if command.existing_releases is ExistingReleasesAction.REPLACE and existing_releases:
            await self._existing_release_replacer.replace(effective_request_id, existing_releases)

        return queued_download_to_async_operation(queued)


__all__ = ["QueueReleaseDownloadUseCase"]
