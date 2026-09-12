"""Reusable stubs for the parts of a protocol a test does not exercise.

The Sonarr and Radarr protocols cover two jobs: reading what is missing, which
the sync use cases need, and managing the library, which only the add-request
flow needs. A fake for one job still has to satisfy the whole protocol, so these
mixins supply the other half and fail loudly if it is ever reached.
"""

from __future__ import annotations

from collections.abc import Sequence

from src.application.interfaces.arr import ArrQualityProfile, ArrRootFolder
from src.application.interfaces.radarr import MovieLookup
from src.application.interfaces.sonarr import SeriesDetails, SeriesLookup
from src.application.interfaces.tmdb import TmdbSearchResult
from src.application.interfaces.tvdb import TvdbSearchResult


class UnusedSonarrLibraryCalls:
    """The library-management half of ``SonarrService``."""

    async def get_root_folders(self) -> list[ArrRootFolder]:
        raise NotImplementedError

    async def get_quality_profiles(self) -> list[ArrQualityProfile]:
        raise NotImplementedError

    async def search_series(self, term: str) -> list[SeriesLookup]:
        raise NotImplementedError

    async def lookup_series(self, tvdb_id: int) -> SeriesLookup | None:
        raise NotImplementedError

    async def add_series(
        self,
        *,
        tvdb_id: int,
        root_folder_path: str,
        quality_profile_id: int,
        monitored_seasons: Sequence[int],
    ) -> int:
        raise NotImplementedError

    async def set_season_monitoring(
        self,
        series_id: int,
        monitored_seasons: Sequence[int],
    ) -> None:
        raise NotImplementedError

    async def wait_for_series_episodes(
        self,
        series_id: int,
        season_numbers: Sequence[int],
        timeout_seconds: float | None = None,
    ) -> SeriesDetails:
        raise NotImplementedError


class UnusedRadarrLibraryCalls:
    """The library-management half of ``RadarrService``."""

    async def get_root_folders(self) -> list[ArrRootFolder]:
        raise NotImplementedError

    async def get_quality_profiles(self) -> list[ArrQualityProfile]:
        raise NotImplementedError

    async def search_movies(self, term: str) -> list[MovieLookup]:
        raise NotImplementedError

    async def lookup_movie(self, tmdb_id: int) -> MovieLookup | None:
        raise NotImplementedError

    async def add_movie(
        self,
        *,
        tmdb_id: int,
        root_folder_path: str,
        quality_profile_id: int,
    ) -> int:
        raise NotImplementedError

    async def set_movie_monitored(self, movie_id: int) -> None:
        raise NotImplementedError


class UnusedTvdbSearch:
    """The search half of ``TvdbService``."""

    async def search_series(
        self,
        query: str,
        limit: int = 20,
        languages: Sequence[str] | None = None,
    ) -> list[TvdbSearchResult]:
        raise NotImplementedError


class UnusedTmdbSearch:
    """The search half of ``TmdbService``."""

    async def search_movies(
        self,
        query: str,
        limit: int = 20,
        languages: Sequence[str] | None = None,
    ) -> list[TmdbSearchResult]:
        raise NotImplementedError


__all__ = [
    "UnusedRadarrLibraryCalls",
    "UnusedSonarrLibraryCalls",
    "UnusedTmdbSearch",
    "UnusedTvdbSearch",
]
