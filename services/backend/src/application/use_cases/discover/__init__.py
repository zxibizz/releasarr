"""Add-request use cases: search metadata providers and add to Sonarr/Radarr."""

from .add_request import AddMediaRequestCommand, AddMediaRequestUseCase
from .dto import (
    LibraryFolderDTO,
    MediaSearchResultDTO,
    RootFolderDTO,
    SeasonOptionDTO,
    SeriesSeasonsDTO,
)
from .exceptions import (
    DisallowedRootFolderError,
    InvalidRootFolderError,
    LibraryFolderUnavailableError,
    MediaNotFoundError,
    MetadataProviderUnavailableError,
    NoQualityProfileError,
    SeasonSelectionError,
    SeasonsUnmanageableError,
)
from .library_folder import (
    GetLibraryFolderUseCase,
    MoveLibraryFolderCommand,
    MoveLibraryFolderUseCase,
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
    "DisallowedRootFolderError",
    "GetLibraryFolderUseCase",
    "InvalidRootFolderError",
    "LibraryFolderDTO",
    "LibraryFolderUnavailableError",
    "ListRequestSeasonsUseCase",
    "ListRootFoldersUseCase",
    "ListSeasonOptionsUseCase",
    "MediaNotFoundError",
    "MediaSearchResultDTO",
    "MetadataProviderUnavailableError",
    "MoveLibraryFolderCommand",
    "MoveLibraryFolderUseCase",
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
