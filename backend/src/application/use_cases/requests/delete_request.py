"""Delete media requests."""

from __future__ import annotations

from src.application.interfaces.media_requests import MediaRequestRepository
from src.application.use_cases.requests.exceptions import MediaRequestNotFoundError


class DeleteMediaRequestUseCase:
    """Use case responsible for removing media requests."""

    def __init__(self, repository: MediaRequestRepository) -> None:
        self._repository = repository

    async def execute(self, request_id: str) -> None:
        deleted = await self._repository.delete_request(request_id)
        if not deleted:
            raise MediaRequestNotFoundError(request_id)


__all__ = ["DeleteMediaRequestUseCase"]
