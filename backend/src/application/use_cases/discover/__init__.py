"""Add-request use cases: search metadata providers and add to Sonarr/Radarr."""

from .add_request import AddMediaRequestCommand, AddMediaRequestUseCase
from .dto import (
    MediaSearchResultDTO,
    RootFolderDTO,
    SeasonOptionDTO,
    SeriesSeasonsDTO,
)
from .exceptions import (
    InvalidRootFolderError,
    MediaNotFoundError,
    MetadataProviderUnavailableError,
    NoQualityProfileError,
    SeasonSelectionError,
)
from .list_root_folders import ListRootFoldersUseCase
from .list_season_options import ListSeasonOptionsUseCase
from .search_media import SearchMediaUseCase

__all__ = [
    "AddMediaRequestCommand",
    "AddMediaRequestUseCase",
    "InvalidRootFolderError",
    "ListRootFoldersUseCase",
    "ListSeasonOptionsUseCase",
    "MediaNotFoundError",
    "MediaSearchResultDTO",
    "MetadataProviderUnavailableError",
    "NoQualityProfileError",
    "RootFolderDTO",
    "SearchMediaUseCase",
    "SeasonOptionDTO",
    "SeasonSelectionError",
    "SeriesSeasonsDTO",
]
