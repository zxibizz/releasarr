"""Register new releases sourced from external providers."""

from __future__ import annotations

from collections import OrderedDict

from src.application.interfaces.releases import CreateReleaseData, ReleaseRepository
from src.application.use_cases.releases.commands import CreateReleaseCommand
from src.application.use_cases.releases.dto import ReleaseDTO
from src.application.use_cases.releases.exceptions import ReleaseConflictError
from src.application.use_cases.releases.mappers import record_to_dto
from src.application.use_cases.requests.recompute_state import RecomputeRequestStateUseCase
from src.application.utility.magnet import parse_magnet
from src.core.logging import get_logger
from src.domain.enums import LogComponent

_logger = get_logger(LogComponent.USECASE_CREATE_RELEASE)


class CreateReleaseUseCase:
    """Use case responsible for creating release records."""

    def __init__(
        self,
        repository: ReleaseRepository,
        recompute_state: RecomputeRequestStateUseCase,
    ) -> None:
        self._repository = repository
        self._recompute_state = recompute_state

    async def execute(self, command: CreateReleaseCommand) -> ReleaseDTO:
        request_ids = self._normalise_request_ids(command.request_ids)
        if not request_ids:
            raise ValueError("at least one request_id must be supplied")

        magnet = parse_magnet(command.magnet_link)
        release_id = command.id or magnet.info_hash

        if await self._repository.get_release(release_id) is not None:
            raise ReleaseConflictError(release_id)

        data = CreateReleaseData(
            magnet_link=command.magnet_link,
            request_ids=request_ids,
            name=command.name or magnet.display_name,
            id=release_id,
            source=command.source or "",
            quality=command.quality or "",
        )
        record = await self._repository.create_release(data)

        try:
            await self._recompute_state.execute(request_ids)
        except Exception as exc:  # pragma: no cover - defensive
            _logger.warning(
                "Failed to settle requests for a created release",
                release_id=record.id,
                error=str(exc),
            )

        return record_to_dto(record)

    def _normalise_request_ids(self, request_ids: list[str]) -> list[str]:
        ordered = OrderedDict((request_id, None) for request_id in request_ids if request_id)
        return list(ordered.keys())


__all__ = ["CreateReleaseUseCase"]
