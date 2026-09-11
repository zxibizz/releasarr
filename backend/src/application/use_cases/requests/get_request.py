"""Retrieve a single media request."""

from __future__ import annotations

from src.application.interfaces.media_requests import MediaRequestRepository
from src.application.use_cases.requests.dto import MediaRequestDTO
from src.application.use_cases.requests.exceptions import MediaRequestNotFoundError
from src.application.use_cases.requests.mappers import record_to_dto


class GetMediaRequestUseCase:
    """Use case for loading a single media request."""

    def __init__(self, repository: MediaRequestRepository) -> None:
        self._repository = repository

    async def execute(self, request_id: str) -> MediaRequestDTO:
        record = await self._repository.get_request(request_id)
        if record is None:
            raise MediaRequestNotFoundError(request_id)
        return record_to_dto(record)


__all__ = ["GetMediaRequestUseCase"]
