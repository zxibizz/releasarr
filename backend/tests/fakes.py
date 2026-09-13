"""Fakes for the services and repositories the use cases are built on.

Two kinds live here. The ``Unused*`` mixins cover the half of a protocol a test
does not exercise: the Sonarr and Radarr protocols each do two jobs - reading
what is missing, which the sync use cases need, and managing the library, which
the request flows need - and a fake for one job still has to satisfy the whole
protocol, so the mixins supply the other half and fail loudly if it is reached.
The rest are working fakes, holding their library or their requests in a dict
and recording the calls that change it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import fields
from datetime import UTC, datetime
from typing import Any

from src.application.interfaces.arr import ArrQualityProfile, ArrRootFolder
from src.application.interfaces.media_requests import (
    CreateMediaRequestData,
    MediaRequestRecord,
    MediaRequestRepository,
    UpdateMediaRequestData,
)
from src.application.interfaces.radarr import MovieDetails, MovieImportFile, MovieLookup
from src.application.interfaces.sonarr import (
    ManualImportFile,
    MissingSeriesRecord,
    SeriesDetails,
    SeriesLookup,
    SeriesSeasonDetails,
    SonarrEpisode,
)
from src.application.interfaces.tmdb import TmdbMovieMetadata, TmdbSearchResult
from src.application.interfaces.tvdb import TvdbSearchResult, TvdbSeriesMetadata
from src.application.utility.sentinels import UNSET
from src.domain.enums import MediaRequestStatus, MediaType


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
        monitor_new_seasons: bool = False,
    ) -> int:
        raise NotImplementedError

    async def apply_season_monitoring(
        self,
        series_id: int,
        *,
        monitor: Sequence[int] = (),
        unmonitor: Sequence[int] = (),
        monitor_new_seasons: bool | None = None,
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

    async def set_movie_monitored(self, movie_id: int, *, monitored: bool = True) -> None:
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


def make_record(
    request_id: str,
    *,
    media_type: MediaType = MediaType.SERIES,
    season_number: int | None = None,
    sonarr_series_id: int | None = None,
    radarr_movie_id: int | None = None,
    status: MediaRequestStatus = MediaRequestStatus.PENDING,
) -> MediaRequestRecord:
    now = datetime.now(UTC)
    return MediaRequestRecord(
        id=request_id,
        media_type=media_type,
        status=status,
        title=f"Request {request_id}",
        year=2020,
        overview=None,
        poster_url=None,
        genres=[],
        runtime_minutes=None,
        imdb_id=None,
        season_number=season_number,
        total_episodes=10 if season_number is not None else None,
        series_title="Example Show" if season_number is not None else None,
        series_year=2020 if season_number is not None else None,
        sonarr_series_id=sonarr_series_id,
        radarr_movie_id=radarr_movie_id,
        created_at=now,
        updated_at=now,
    )


class FakeMediaRequestRepository(MediaRequestRepository):
    def __init__(self, records: dict[str, MediaRequestRecord] | None = None) -> None:
        self.records = records or {}
        self.created: list[CreateMediaRequestData] = []

    async def list_requests(
        self, *args: Any, **kwargs: Any
    ) -> tuple[list[MediaRequestRecord], int]:
        raise NotImplementedError

    async def create_request(self, data: CreateMediaRequestData) -> MediaRequestRecord:
        self.created.append(data)
        now = datetime.now(UTC)
        record = MediaRequestRecord(
            **{
                field.name: getattr(data, field.name)
                for field in fields(MediaRequestRecord)
                if field.name not in {"created_at", "updated_at"}
            },
            created_at=now,
            updated_at=now,
        )
        self.records[record.id] = record
        return record

    async def get_request(self, request_id: str) -> MediaRequestRecord | None:
        return self.records.get(request_id)

    async def update_request(
        self,
        request_id: str,
        data: UpdateMediaRequestData,
    ) -> MediaRequestRecord | None:
        record = self.records.get(request_id)
        if record is None:
            return None
        for field in fields(UpdateMediaRequestData):
            value = getattr(data, field.name)
            if value is not UNSET:
                setattr(record, field.name, value)
        return record

    async def delete_request(self, request_id: str) -> bool:
        return self.records.pop(request_id, None) is not None

    async def find_by_sonarr(
        self,
        *,
        sonarr_series_id: int,
        season_number: int,
    ) -> MediaRequestRecord | None:
        for record in self.records.values():
            if (
                record.sonarr_series_id == sonarr_series_id
                and record.season_number == season_number
            ):
                return record
        return None

    async def list_sonarr_requests(self) -> list[MediaRequestRecord]:
        return [record for record in self.records.values() if record.sonarr_series_id is not None]

    async def find_by_radarr(self, *, radarr_movie_id: int) -> MediaRequestRecord | None:
        for record in self.records.values():
            if record.radarr_movie_id == radarr_movie_id:
                return record
        return None

    async def list_radarr_requests(self) -> list[MediaRequestRecord]:
        return [record for record in self.records.values() if record.radarr_movie_id is not None]


class FakeSonarrService:
    """A Sonarr whose library is a dict, recording the calls that change it."""

    def __init__(
        self,
        *,
        lookups: dict[int, SeriesLookup] | None = None,
        catalogue: dict[int, SeriesDetails] | None = None,
        search_results: list[SeriesLookup] | None = None,
        root_folders: list[ArrRootFolder] | None = None,
        quality_profiles: list[ArrQualityProfile] | None = None,
        search_error: Exception | None = None,
    ) -> None:
        self._lookups = lookups or {}
        self._catalogue = catalogue or {}
        self._search_results = search_results or []
        # An empty list is a deliberate "Sonarr reports none", not "use the default".
        self._root_folders = (
            [ArrRootFolder(path="/tv", free_space=1024)] if root_folders is None else root_folders
        )
        self._quality_profiles = (
            [ArrQualityProfile(id=4, name="Any")] if quality_profiles is None else quality_profiles
        )
        self._search_error = search_error
        self.added: list[dict[str, Any]] = []
        self.monitored: list[dict[str, Any]] = []
        self.waited: list[tuple[int, list[int]]] = []

    async def get_missing_series(self) -> list[MissingSeriesRecord]:
        return []

    async def get_series(self, series_id: int) -> SeriesDetails:
        return self._catalogue[series_id]

    async def get_episodes(self, series_id: int) -> list[SonarrEpisode]:
        return []

    async def manual_import(self, files: list[ManualImportFile]) -> bool:
        return True

    async def get_root_folders(self) -> list[ArrRootFolder]:
        return self._root_folders

    async def get_quality_profiles(self) -> list[ArrQualityProfile]:
        return self._quality_profiles

    async def search_series(self, term: str) -> list[SeriesLookup]:
        if self._search_error is not None:
            raise self._search_error
        return self._search_results

    async def lookup_series(self, tvdb_id: int) -> SeriesLookup | None:
        return self._lookups.get(tvdb_id)

    async def add_series(
        self,
        *,
        tvdb_id: int,
        root_folder_path: str,
        quality_profile_id: int,
        monitored_seasons: Sequence[int],
        monitor_new_seasons: bool = False,
    ) -> int:
        self.added.append(
            {
                "tvdb_id": tvdb_id,
                "root_folder_path": root_folder_path,
                "quality_profile_id": quality_profile_id,
                "monitored_seasons": list(monitored_seasons),
                "monitor_new_seasons": monitor_new_seasons,
            }
        )
        return 12

    async def apply_season_monitoring(
        self,
        series_id: int,
        *,
        monitor: Sequence[int] = (),
        unmonitor: Sequence[int] = (),
        monitor_new_seasons: bool | None = None,
    ) -> None:
        self.monitored.append(
            {
                "series_id": series_id,
                "monitor": list(monitor),
                "unmonitor": list(unmonitor),
                "monitor_new_seasons": monitor_new_seasons,
            }
        )
        # Mirrored onto the catalogue so a caller that reads the series back sees
        # the monitoring it just asked for, as it would from Sonarr itself.
        details = self._catalogue.get(series_id)
        if details is None:
            return
        if monitor_new_seasons is not None:
            details.monitor_new_seasons = monitor_new_seasons
        for season_number in monitor:
            season = details.seasons.get(season_number)
            if season is not None:
                season.monitored = True
        for season_number in unmonitor:
            season = details.seasons.get(season_number)
            if season is not None:
                season.monitored = False

    async def wait_for_series_episodes(
        self,
        series_id: int,
        season_numbers: Sequence[int],
        timeout_seconds: float | None = None,
    ) -> SeriesDetails:
        self.waited.append((series_id, list(season_numbers)))
        return self._catalogue[series_id]


class FakeRadarrService:
    """A Radarr whose library is a dict, recording the calls that change it."""

    def __init__(
        self,
        *,
        lookups: dict[int, MovieLookup] | None = None,
        catalogue: dict[int, MovieDetails] | None = None,
        search_results: list[MovieLookup] | None = None,
        root_folders: list[ArrRootFolder] | None = None,
        quality_profiles: list[ArrQualityProfile] | None = None,
        search_error: Exception | None = None,
    ) -> None:
        self._lookups = lookups or {}
        self._catalogue = catalogue or {}
        self._search_results = search_results or []
        self._root_folders = (
            [ArrRootFolder(path="/movies", free_space=2048)]
            if root_folders is None
            else root_folders
        )
        self._quality_profiles = (
            [ArrQualityProfile(id=2, name="HD")] if quality_profiles is None else quality_profiles
        )
        self._search_error = search_error
        self.added: list[dict[str, Any]] = []
        self.monitored: list[tuple[int, bool]] = []

    async def get_missing_movies(self) -> list[MovieDetails]:
        return []

    async def get_movie(self, movie_id: int) -> MovieDetails:
        return self._catalogue[movie_id]

    async def manual_import(self, files: list[MovieImportFile]) -> bool:
        return True

    async def get_root_folders(self) -> list[ArrRootFolder]:
        return self._root_folders

    async def get_quality_profiles(self) -> list[ArrQualityProfile]:
        return self._quality_profiles

    async def search_movies(self, term: str) -> list[MovieLookup]:
        if self._search_error is not None:
            raise self._search_error
        return self._search_results

    async def lookup_movie(self, tmdb_id: int) -> MovieLookup | None:
        return self._lookups.get(tmdb_id)

    async def add_movie(
        self,
        *,
        tmdb_id: int,
        root_folder_path: str,
        quality_profile_id: int,
    ) -> int:
        self.added.append(
            {
                "tmdb_id": tmdb_id,
                "root_folder_path": root_folder_path,
                "quality_profile_id": quality_profile_id,
            }
        )
        return 31

    async def set_movie_monitored(self, movie_id: int, *, monitored: bool = True) -> None:
        self.monitored.append((movie_id, monitored))


class FakeTvdbService:
    def __init__(
        self,
        *,
        search_results: list[TvdbSearchResult] | None = None,
        metadata: dict[int, TvdbSeriesMetadata] | None = None,
        search_error: Exception | None = None,
    ) -> None:
        self._search_results = search_results or []
        self._metadata = metadata or {}
        self._search_error = search_error
        self.search_languages: list[list[str]] = []

    async def get_series(
        self,
        tvdb_id: int,
        languages: Sequence[str] | None = None,
    ) -> TvdbSeriesMetadata:
        return self._metadata[tvdb_id]

    async def search_series(
        self,
        query: str,
        limit: int = 20,
        languages: Sequence[str] | None = None,
    ) -> list[TvdbSearchResult]:
        self.search_languages.append(list(languages or ()))
        if self._search_error is not None:
            raise self._search_error
        return self._search_results


class FakeTmdbService:
    def __init__(
        self,
        *,
        search_results: list[TmdbSearchResult] | None = None,
        metadata: dict[int, TmdbMovieMetadata] | None = None,
        search_error: Exception | None = None,
    ) -> None:
        self._search_results = search_results or []
        self._metadata = metadata or {}
        self._search_error = search_error
        self.search_languages: list[list[str]] = []

    async def get_movie(
        self,
        tmdb_id: int,
        languages: Sequence[str] | None = None,
    ) -> TmdbMovieMetadata:
        return self._metadata[tmdb_id]

    async def search_movies(
        self,
        query: str,
        limit: int = 20,
        languages: Sequence[str] | None = None,
    ) -> list[TmdbSearchResult]:
        self.search_languages.append(list(languages or ()))
        if self._search_error is not None:
            raise self._search_error
        return self._search_results


def make_series_details(
    series_id: int = 12,
    *,
    seasons: dict[int, tuple[int, bool]] | None = None,
    monitor_new_seasons: bool = False,
) -> SeriesDetails:
    """Build Sonarr series details from ``{season: (episode_count, monitored)}``."""

    resolved = seasons or {1: (10, True), 2: (8, False)}
    return SeriesDetails(
        id=series_id,
        title="Example Show",
        year=2020,
        overview="An overview",
        poster_url="http://poster",
        imdb_id="tt1234567",
        tvdb_id=555,
        genres=["Drama"],
        seasons={
            season_number: SeriesSeasonDetails(
                season_number=season_number,
                episode_count=episode_count,
                total_episode_count=episode_count,
                episode_file_count=0,
                monitored=season_monitored,
            )
            for season_number, (episode_count, season_monitored) in resolved.items()
        },
        monitor_new_seasons=monitor_new_seasons,
    )


def make_movie_details(movie_id: int = 31) -> MovieDetails:
    return MovieDetails(
        id=movie_id,
        title="Example Movie",
        year=2021,
        overview="An overview",
        poster_url="http://poster",
        imdb_id="tt7654321",
        tmdb_id=777,
        genres=["Sci-Fi"],
        runtime_minutes=116,
    )


__all__ = [
    "FakeMediaRequestRepository",
    "FakeRadarrService",
    "FakeSonarrService",
    "FakeTmdbService",
    "FakeTvdbService",
    "UnusedRadarrLibraryCalls",
    "UnusedSonarrLibraryCalls",
    "UnusedTmdbSearch",
    "UnusedTvdbSearch",
    "make_movie_details",
    "make_record",
    "make_series_details",
]
