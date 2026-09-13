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
    SeasonsUnmanageableError,
)
from .list_root_folders import ListRootFoldersUseCase
from .list_season_options import ListSeasonOptionsUseCase
from .manage_seasons import (
    ListRequestSeasonsUseCase,
    UpdateRequestSeasonsCommand,
    UpdateRequestSeasonsUseCase,
)
from .search_media import SearchMediaUseCase

__all__ = [
    "AddMediaRequestCommand",
    "AddMediaRequestUseCase",
    "InvalidRootFolderError",
    "ListRequestSeasonsUseCase",
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
    "SeasonsUnmanageableError",
    "SeriesSeasonsDTO",
    "UpdateRequestSeasonsCommand",
    "UpdateRequestSeasonsUseCase",
]
