"""Search external providers for candidate releases."""

from __future__ import annotations

from src.application.interfaces.releases import ReleaseSearchService
from src.application.use_cases.releases.commands import SearchReleaseSourcesCommand
from src.application.use_cases.releases.dto import ReleaseSearchResponseDTO
from src.application.use_cases.releases.mappers import search_results_to_dto


class SearchReleaseSourcesUseCase:
    """Use case orchestrating release source searches."""

    def __init__(self, search_service: ReleaseSearchService) -> None:
        self._search_service = search_service

    async def execute(self, command: SearchReleaseSourcesCommand) -> ReleaseSearchResponseDTO:
        results = await self._search_service.search(command.query, request_id=command.request_id)
        return search_results_to_dto(results)


__all__ = ["SearchReleaseSourcesUseCase"]
