"""Retrieve release details."""

from __future__ import annotations

from src.application.interfaces.releases import ReleaseRepository
from src.application.use_cases.releases.dto import ReleaseDTO
from src.application.use_cases.releases.exceptions import ReleaseNotFoundError
from src.application.use_cases.releases.mappers import record_to_dto


class GetReleaseUseCase:
    """Use case fetching a release by its identifier."""

    def __init__(self, repository: ReleaseRepository) -> None:
        self._repository = repository

    async def execute(self, release_id: str) -> ReleaseDTO:
        record = await self._repository.get_release(release_id)
        if record is None:
            raise ReleaseNotFoundError(release_id)

        return record_to_dto(record)


__all__ = ["GetReleaseUseCase"]
