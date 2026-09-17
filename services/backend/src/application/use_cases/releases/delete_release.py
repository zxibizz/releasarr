"""Delete releases by identifier."""

from __future__ import annotations

from src.application.interfaces.releases import ReleaseDownloadService, ReleaseRepository
from src.application.interfaces.request_warnings import RequestWarningRepository
from src.application.use_cases.releases.exceptions import ReleaseNotFoundError
from src.application.use_cases.requests.recompute_state import RecomputeRequestStateUseCase
from src.core.logging import get_logger
from src.domain.enums import LogComponent


class DeleteReleaseUseCase:
    """Use case removing a release and its associated files."""

    def __init__(
        self,
        repository: ReleaseRepository,
        download_service: ReleaseDownloadService,
        warning_repository: RequestWarningRepository,
        recompute_state: RecomputeRequestStateUseCase,
    ) -> None:
        self._repository = repository
        self._download_service = download_service
        self._warning_repository = warning_repository
        self._recompute_state = recompute_state
        self._logger = get_logger(LogComponent.USECASE_DELETE_RELEASE)

    async def execute(self, release_id: str) -> None:
        release = await self._repository.get_release(release_id)
        if release:
            try:
                await self._download_service.delete_download(release.info_hash)
            except Exception:
                self._logger.warning(
                    "Failed to delete release from downloader",
                    release_id=release_id,
                    info_hash=release.info_hash,
                )

        deleted = await self._repository.delete_release(release_id)
        if not deleted:
            raise ReleaseNotFoundError(release_id)

        if release:
            await self._settle_requests(release.id, release.request_ids)

    async def _settle_requests(self, release_id: str, request_ids: list[str]) -> None:
        try:
            # Not implied by the FK cascade - see the warning repository's
            # own docstring for why removal here is explicit.
            await self._warning_repository.delete_for_release(release_id)
            # A release deleted out from under a request can resolve an
            # overlap for whichever releases it still has left, and can be
            # the request's only release, which must not stay in flight.
            await self._recompute_state.execute(request_ids)
        except Exception as exc:  # pragma: no cover - defensive
            self._logger.warning(
                "Failed to settle requests for a deleted release",
                release_id=release_id,
                error=str(exc),
            )


__all__ = ["DeleteReleaseUseCase"]
