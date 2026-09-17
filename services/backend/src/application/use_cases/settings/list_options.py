"""Look up the values a settings field can hold, from the service that owns them."""

from __future__ import annotations

from dataclasses import dataclass

from src.application.interfaces.indexers import IndexerCategoryDirectory
from src.application.interfaces.radarr import RadarrService
from src.application.interfaces.releases import DownloadClientDirectory
from src.application.interfaces.sonarr import SonarrService
from src.application.use_cases.indexers.exceptions import ProwlarrNotConfiguredError
from src.application.use_cases.releases.exceptions import QbittorrentNotConfiguredError


@dataclass(slots=True)
class QualityProfileOptionDTO:
    profile_id: int
    name: str


@dataclass(slots=True)
class IndexerCategoryOptionDTO:
    category_id: int
    name: str


class ListQualityProfilesUseCase:
    """Return the quality profiles Sonarr or Radarr is configured with."""

    def __init__(self, *, sonarr_service: SonarrService, radarr_service: RadarrService) -> None:
        self._sonarr = sonarr_service
        self._radarr = radarr_service

    async def execute(self, integration: str) -> list[QualityProfileOptionDTO]:
        service: SonarrService | RadarrService = (
            self._sonarr if integration == "sonarr" else self._radarr
        )
        profiles = await service.get_quality_profiles()
        return [
            QualityProfileOptionDTO(profile_id=profile.id, name=profile.name)
            for profile in profiles
        ]


class ListIndexerCategoriesUseCase:
    """Return the search categories the configured indexers accept."""

    def __init__(self, *, directory: IndexerCategoryDirectory) -> None:
        self._directory = directory

    async def execute(self) -> list[IndexerCategoryOptionDTO]:
        if not self._directory.is_configured:
            raise ProwlarrNotConfiguredError
        return [
            IndexerCategoryOptionDTO(category_id=category.category_id, name=category.name)
            for category in await self._directory.list_categories()
        ]


class ListDownloadCategoriesUseCase:
    """Return the categories the download client already has."""

    def __init__(self, *, client: DownloadClientDirectory) -> None:
        self._client = client

    async def execute(self) -> list[str]:
        if not self._client.is_configured:
            raise QbittorrentNotConfiguredError
        return list(await self._client.list_categories())


__all__ = [
    "IndexerCategoryOptionDTO",
    "ListDownloadCategoriesUseCase",
    "ListIndexerCategoriesUseCase",
    "ListQualityProfilesUseCase",
    "QualityProfileOptionDTO",
]
