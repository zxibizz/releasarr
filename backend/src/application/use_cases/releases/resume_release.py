"""Resume paused release downloads."""

from __future__ import annotations

from src.application.interfaces.releases import ReleaseLifecycleService, ReleaseRepository
from src.application.use_cases.releases.dto import AsyncOperationDTO
from src.application.use_cases.releases.exceptions import (
    ReleaseActionNotAllowedError,
    ReleaseNotFoundError,
)


class ResumeReleaseUseCase:
    """Use case requesting a release download resume."""

    def __init__(
        self,
        repository: ReleaseRepository,
        lifecycle_service: ReleaseLifecycleService,
    ) -> None:
        self._repository = repository
        self._lifecycle_service = lifecycle_service

    async def execute(self, release_id: str) -> AsyncOperationDTO:
        release = await self._repository.get_release(release_id)
        if release is None:
            raise ReleaseNotFoundError(release_id)

        accepted = await self._lifecycle_service.resume(release.info_hash)
        if not accepted:
            raise ReleaseActionNotAllowedError(release_id, "resume")

        return AsyncOperationDTO(
            operation="resume_release",
            status="accepted",
            operation_id=None,
            location=None,
            message=None,
            resource_id=release_id,
            details={"release_id": release_id, "previous_status": release.status.value},
        )


__all__ = ["ResumeReleaseUseCase"]
