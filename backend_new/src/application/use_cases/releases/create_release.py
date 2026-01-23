"""Register new releases sourced from external providers."""

from __future__ import annotations

from collections import OrderedDict

from src.application.interfaces.releases import CreateReleaseData, ReleaseRepository
from src.application.use_cases.releases.commands import CreateReleaseCommand
from src.application.use_cases.releases.dto import ReleaseDTO
from src.application.use_cases.releases.mappers import record_to_dto


class CreateReleaseUseCase:
    """Use case responsible for creating release records."""

    def __init__(self, repository: ReleaseRepository) -> None:
        self._repository = repository

    async def execute(self, command: CreateReleaseCommand) -> ReleaseDTO:
        request_ids = self._normalise_request_ids(command.request_ids)
        if not request_ids:
            raise ValueError("at least one request_id must be supplied")

        data = CreateReleaseData(
            magnet_link=command.magnet_link,
            request_ids=request_ids,
            name=command.name,
            id=command.id,
            source=command.source or "",
            quality=command.quality or "",
        )
        record = await self._repository.create_release(data)
        return record_to_dto(record)

    def _normalise_request_ids(self, request_ids: list[str]) -> list[str]:
        ordered = OrderedDict((request_id, None) for request_id in request_ids if request_id)
        return list(ordered.keys())


__all__ = ["CreateReleaseUseCase"]
