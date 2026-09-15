"""Retrieve release details."""

from __future__ import annotations

from src.application.interfaces.releases import ReleaseRepository
from src.application.interfaces.request_warnings import RequestWarningRepository
from src.application.use_cases.releases.dto import ReleaseDTO
from src.application.use_cases.releases.exceptions import ReleaseNotFoundError
from src.application.use_cases.releases.mappers import record_to_dto
from src.application.use_cases.releases.warnings import rows_to_release_warnings


class GetReleaseUseCase:
    """Use case fetching a release by its identifier."""

    def __init__(
        self,
        repository: ReleaseRepository,
        warning_repository: RequestWarningRepository | None = None,
    ) -> None:
        self._repository = repository
        self._warning_repository = warning_repository

    async def execute(self, release_id: str) -> ReleaseDTO:
        record = await self._repository.get_release(release_id)
        if record is None:
            raise ReleaseNotFoundError(release_id)

        warnings = []
        if self._warning_repository is not None:
            by_release = await self._warning_repository.list_for_releases([release_id])
            warnings = rows_to_release_warnings(by_release.get(release_id, []))

        return record_to_dto(record, warnings)


__all__ = ["GetReleaseUseCase"]
