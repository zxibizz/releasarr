"""Retrieve release details."""

from __future__ import annotations

from src.application.interfaces.releases import ReleaseRepository
from src.application.use_cases.releases.dto import ReleaseDTO
from src.application.use_cases.releases.exceptions import ReleaseNotFoundError
from src.application.use_cases.releases.mappers import record_to_dto
from src.application.use_cases.releases.warnings import ReleaseWarningEvaluator


class GetReleaseUseCase:
    """Use case fetching a release by its identifier."""

    def __init__(
        self,
        repository: ReleaseRepository,
        warning_evaluator: ReleaseWarningEvaluator | None = None,
    ) -> None:
        self._repository = repository
        self._warning_evaluator = warning_evaluator or ReleaseWarningEvaluator()

    async def execute(self, release_id: str) -> ReleaseDTO:
        record = await self._repository.get_release(release_id)
        if record is None:
            raise ReleaseNotFoundError(release_id)

        related = await self._repository.get_releases_for_requests(record.request_ids)
        warnings = self._warning_evaluator.evaluate(related).get(release_id, [])

        return record_to_dto(record, warnings)


__all__ = ["GetReleaseUseCase"]
