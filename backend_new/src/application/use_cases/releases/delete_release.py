"""Delete releases by identifier."""

from __future__ import annotations

from src.application.interfaces.releases import ReleaseRepository
from src.application.use_cases.releases.exceptions import ReleaseNotFoundError


class DeleteReleaseUseCase:
    """Use case removing a release and its associated files."""

    def __init__(self, repository: ReleaseRepository) -> None:
        self._repository = repository

    async def execute(self, release_id: str) -> None:
        deleted = await self._repository.delete_release(release_id)
        if not deleted:
            raise ReleaseNotFoundError(release_id)


__all__ = ["DeleteReleaseUseCase"]
