"""Offer the mappings automapping would make for a release's files."""

from __future__ import annotations

from src.application.interfaces.releases import ReleaseRepository
from src.application.use_cases.releases.auto_mapping import ReleaseAutoMapper
from src.application.use_cases.releases.dto import ReleaseFileMappingSuggestionDTO
from src.application.use_cases.releases.exceptions import ReleaseNotFoundError
from src.application.use_cases.releases.mappers import mapping_to_dto


class SuggestReleaseFileMappingsUseCase:
    """Use case proposing file mappings without applying any of them.

    The grab and the export map on their own; this serves the mapping form,
    which needs the same proposals for a release those passes could not resolve
    and for one whose requests have changed since. Nothing is stored, so the
    user remains the one who decides what a file is.
    """

    def __init__(self, repository: ReleaseRepository, auto_mapper: ReleaseAutoMapper) -> None:
        self._repository = repository
        self._auto_mapper = auto_mapper

    async def execute(self, release_id: str) -> list[ReleaseFileMappingSuggestionDTO]:
        release = await self._repository.get_release(release_id)
        if release is None:
            raise ReleaseNotFoundError(release_id)

        updates, _ = await self._auto_mapper.suggest(release)

        # A proposal to unmap is not one worth making: the matcher only ever
        # clears a mapping it just set, and the form already offers that itself.
        return [
            ReleaseFileMappingSuggestionDTO(file_id=update.file_id, request_mapping=mapping)
            for update in updates
            if (mapping := mapping_to_dto(update.mapping)) is not None
        ]


__all__ = ["SuggestReleaseFileMappingsUseCase"]
