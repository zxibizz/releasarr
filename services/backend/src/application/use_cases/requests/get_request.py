"""Retrieve a single media request."""

from __future__ import annotations

from src.application.interfaces.media_requests import MediaRequestRepository
from src.application.interfaces.request_warnings import RequestWarningRepository
from src.application.use_cases.requests.dto import MediaRequestDTO
from src.application.use_cases.requests.exceptions import MediaRequestNotFoundError
from src.application.use_cases.requests.mappers import record_to_dto


class GetMediaRequestUseCase:
    """Use case for loading a single media request."""

    def __init__(
        self,
        repository: MediaRequestRepository,
        warning_repository: RequestWarningRepository,
    ) -> None:
        self._repository = repository
        self._warning_repository = warning_repository

    async def execute(self, request_id: str) -> MediaRequestDTO:
        record = await self._repository.get_request(request_id)
        if record is None:
            raise MediaRequestNotFoundError(request_id)

        by_request = await self._warning_repository.list_for_requests([request_id])
        warnings = by_request.get(request_id, [])

        return record_to_dto(record, warnings)


__all__ = ["GetMediaRequestUseCase"]
