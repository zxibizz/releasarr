"""Fakes for the services and repositories the use cases are built on.

Two kinds live here. The ``Unused*`` mixins cover the half of a protocol a test
does not exercise: the Sonarr and Radarr protocols each do two jobs - reading
what is missing, which the sync use cases need, and managing the library, which
the request flows need - and a fake for one job still has to satisfy the whole
protocol, so the mixins supply the other half and fail loudly if it is reached.
The rest are working fakes, holding their library or their requests in a dict
and recording the calls that change it.

The ``InMemory*`` release services are complete stand-ins for the three release
ports. They were the container's fallback until an unconfigured provider began
reporting ``is_configured``, which left them with no production caller; a test
that wants a release flow to run without a download client is what they are for.
"""

from __future__ import annotations

import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, field, fields
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.application.interfaces.arr import ArrQualityProfile, ArrRootFolder
from src.application.interfaces.indexers import (
    IndexerEventPage,
    IndexerLogPage,
    IndexerRecord,
    IndexerTestResultRecord,
)
from src.application.interfaces.media_requests import (
    CreateMediaRequestData,
    MediaRequestRecord,
    MediaRequestRepository,
    UpdateMediaRequestData,
)
from src.application.interfaces.radarr import MovieDetails, MovieImportFile, MovieLookup
from src.application.interfaces.releases import (
    CreateReleaseData,
    FileMappingUpdateData,
    QueuedDownload,
    ReleaseDownloadService,
    ReleaseLifecycleService,
    ReleaseRecord,
    ReleaseSearchResultRecord,
    ReleaseSearchResults,
    ReleaseSearchService,
    ReleaseTorrentState,
)
from src.application.interfaces.request_warnings import RequestWarningRecord
from src.application.interfaces.sonarr import (
    ManualImportFile,
    MissingSeriesRecord,
    SeriesDetails,
    SeriesLookup,
    SeriesSeasonDetails,
    SonarrEpisode,
)
from src.application.interfaces.sync_jobs import (
    EnqueueSyncJobResult,
    ScheduledTaskRecord,
    SyncJobRecord,
)
from src.application.interfaces.tmdb import TmdbMovieMetadata, TmdbSearchResult
from src.application.interfaces.tvdb import TvdbSearchResult, TvdbSeriesMetadata
from src.application.utility.sentinels import UNSET
from src.domain.enums import (
    IndexerEventType,
    IndexerLogLevel,
    MediaRequestStatus,
    MediaType,
    ReleaseStatus,
    RequestWarningCode,
    SyncJobKind,
    SyncJobStatus,
    SyncJobTrigger,
)


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


class UnusedMediaRequestCalls:
    """Every ``MediaRequestRepository`` call a test might not drive.

    The two syncs read only their own half - Sonarr series or Radarr movies - so
    each test's recording fake implements that half and inherits the other.
    """

    async def list_requests(
        self,
        *,
        page: int,
        per_page: int,
        status: MediaRequestStatus | None,
        media_type: MediaType | None,
        owner_user_id: str | None = None,
        has_warnings: bool | None = None,
    ) -> tuple[list[MediaRequestRecord], int]:
        raise NotImplementedError

    async def create_request(self, data: CreateMediaRequestData) -> MediaRequestRecord:
        raise NotImplementedError

    async def get_request(self, request_id: str) -> MediaRequestRecord | None:
        raise NotImplementedError

    async def update_request(
        self,
        request_id: str,
        data: UpdateMediaRequestData,
    ) -> MediaRequestRecord | None:
        raise NotImplementedError

    async def delete_request(self, request_id: str) -> bool:
        raise NotImplementedError

    async def find_by_sonarr(
        self,
        *,
        sonarr_series_id: int,
        season_number: int,
    ) -> MediaRequestRecord | None:
        raise NotImplementedError

    async def list_sonarr_requests(self) -> list[MediaRequestRecord]:
        raise NotImplementedError

    async def find_by_radarr(self, *, radarr_movie_id: int) -> MediaRequestRecord | None:
        raise NotImplementedError

    async def list_radarr_requests(self) -> list[MediaRequestRecord]:
        raise NotImplementedError


class UnusedReleaseRepositoryCalls:
    """Every ``ReleaseRepository`` call a test might not drive.

    The protocol is as wide as the release flow is, and a given test needs one or
    two of these, so it implements those and inherits the rest.
    """

    async def list_releases(
        self,
        *,
        page: int,
        per_page: int,
        status: ReleaseStatus | None,
        request_id: str | None,
    ) -> tuple[list[ReleaseRecord], int]:
        raise NotImplementedError

    async def create_release(self, data: CreateReleaseData) -> ReleaseRecord:
        raise NotImplementedError

    async def get_release(self, release_id: str) -> ReleaseRecord | None:
        raise NotImplementedError

    async def delete_release(self, release_id: str) -> bool:
        raise NotImplementedError

    async def unlink_request(self, release_id: str, request_id: str) -> bool:
        raise NotImplementedError

    async def get_releases_for_requests(self, request_ids: list[str]) -> list[ReleaseRecord]:
        raise NotImplementedError

    async def list_request_ids_with_releases(self) -> list[str]:
        raise NotImplementedError

    async def update_file_mappings(
        self,
        release_id: str,
        updates: list[FileMappingUpdateData],
    ) -> bool:
        raise NotImplementedError

    async def get_finished_not_exported(self) -> list[ReleaseRecord]:
        raise NotImplementedError

    async def get_potential_outdated_releases(self) -> list[ReleaseRecord]:
        raise NotImplementedError

    async def update_release(self, release_id: str, **kwargs: object) -> bool:
        raise NotImplementedError

    async def count_by_status(self) -> dict[ReleaseStatus, int]:
        raise NotImplementedError


class UnusedReleaseDownloadCalls:
    """Every ``ReleaseDownloadService`` call a test might not drive."""

    async def queue_download(
        self,
        request_id: str,
        release_id: str,
        magnet_link: str,
        torrent_bytes: bytes | None = None,
    ) -> QueuedDownload:
        raise NotImplementedError

    async def delete_download(self, release_id: str) -> None:
        raise NotImplementedError

    async def get_torrent_state(self, info_hash: str) -> ReleaseTorrentState | None:
        raise NotImplementedError

    async def get_download_directory(self, info_hash: str) -> str | None:
        raise NotImplementedError


class UnusedRequestWarningCalls:
    """Every ``RequestWarningRepository`` call a test might not drive."""

    async def replace_for_requests(
        self,
        code: RequestWarningCode,
        request_ids: Sequence[str],
        warnings: Sequence[RequestWarningRecord],
    ) -> None:
        raise NotImplementedError

    async def replace_for_releases(
        self,
        code: RequestWarningCode,
        release_ids: Sequence[str],
        warnings: Sequence[RequestWarningRecord],
    ) -> None:
        raise NotImplementedError

    async def delete_for_release(self, release_id: str) -> None:
        raise NotImplementedError

    async def delete_for_request_release(self, request_id: str, release_id: str) -> None:
        raise NotImplementedError

    async def list_for_requests(
        self, request_ids: Sequence[str]
    ) -> dict[str, list[RequestWarningRecord]]:
        raise NotImplementedError

    async def list_for_releases(
        self, release_ids: Sequence[str]
    ) -> dict[str, list[RequestWarningRecord]]:
        raise NotImplementedError


class UnusedScheduledTaskCalls:
    """Every ``ScheduledTaskRepository`` call a test might not drive."""

    async def list_tasks(self) -> list[ScheduledTaskRecord]:
        raise NotImplementedError

    async def get(self, kind: SyncJobKind) -> ScheduledTaskRecord | None:
        raise NotImplementedError

    async def register(self, *, kind: SyncJobKind, interval_seconds: int) -> ScheduledTaskRecord:
        raise NotImplementedError

    async def record_run(
        self,
        kind: SyncJobKind,
        *,
        status: SyncJobStatus,
        duration_ms: int,
        error: str | None = None,
        executed_at: datetime | None = None,
    ) -> None:
        raise NotImplementedError


class UnusedSyncJobCalls:
    """Every ``SyncJobRepository`` call a test might not drive."""

    async def enqueue(self, *, kind: SyncJobKind, trigger: SyncJobTrigger) -> EnqueueSyncJobResult:
        raise NotImplementedError

    async def enqueue_sequence(
        self, *, kinds: Sequence[SyncJobKind], trigger: SyncJobTrigger
    ) -> list[EnqueueSyncJobResult]:
        raise NotImplementedError

    async def claim_next(self) -> SyncJobRecord | None:
        raise NotImplementedError

    async def finish(
        self,
        job_id: str,
        *,
        status: SyncJobStatus,
        result: dict[str, object] | None = None,
        error: str | None = None,
    ) -> None:
        raise NotImplementedError

    async def get(self, job_id: str) -> SyncJobRecord | None:
        raise NotImplementedError

    async def list_recent(self, *, limit: int = 20) -> list[SyncJobRecord]:
        raise NotImplementedError

    async def fail_running(self, *, error: str) -> int:
        raise NotImplementedError

    async def prune(self, *, keep: int) -> int:
        raise NotImplementedError


class UnusedIndexerDirectoryCalls:
    """Every ``IndexerDirectory`` call a test might not drive.

    The release fan-out only lists indexers and the indexers page only inspects
    them, so each fake implements the one or two calls it needs and inherits the
    rest. Reaching an inherited one fails loudly rather than answering emptily.
    """

    async def list_indexers(self) -> Sequence[IndexerRecord]:
        raise NotImplementedError

    async def list_history(
        self,
        *,
        page: int,
        per_page: int,
        indexer_id: int | None = None,
        event_type: IndexerEventType | None = None,
    ) -> IndexerEventPage:
        raise NotImplementedError

    async def list_logs(
        self,
        *,
        page: int,
        per_page: int,
        min_level: IndexerLogLevel | None = None,
    ) -> IndexerLogPage:
        raise NotImplementedError

    async def test_indexer(self, indexer_id: int) -> IndexerTestResultRecord:
        raise NotImplementedError

    async def test_all_indexers(self) -> Sequence[IndexerTestResultRecord]:
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
        for data_field in fields(UpdateMediaRequestData):
            value = getattr(data, data_field.name)
            if value is not UNSET:
                setattr(record, data_field.name, value)
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
        episodes: dict[int, list[SonarrEpisode]] | None = None,
        search_results: list[SeriesLookup] | None = None,
        root_folders: list[ArrRootFolder] | None = None,
        quality_profiles: list[ArrQualityProfile] | None = None,
        search_error: Exception | None = None,
    ) -> None:
        self._lookups = lookups or {}
        self._catalogue = catalogue or {}
        self._episodes = episodes or {}
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
        return self._episodes.get(series_id, [])

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
        is_configured: bool = True,
    ) -> None:
        self._search_results = search_results or []
        self._metadata = metadata or {}
        self._search_error = search_error
        self.is_configured = is_configured
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
        is_configured: bool = True,
    ) -> None:
        self._search_results = search_results or []
        self._metadata = metadata or {}
        self._search_error = search_error
        self.is_configured = is_configured
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
    downloaded_seasons: Sequence[int] | None = None,
    monitor_new_seasons: bool = False,
) -> SeriesDetails:
    """Build Sonarr series details from ``{season: (episode_count, monitored)}``.

    Seasons named in ``downloaded_seasons`` hold a file per episode; the rest
    hold none, which is the more useful default for a request to be made of.
    """

    resolved = seasons or {1: (10, True), 2: (8, False)}
    downloaded = set(downloaded_seasons or ())
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
                episode_file_count=episode_count if season_number in downloaded else 0,
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


@dataclass(slots=True)
class InMemoryReleaseLifecycleService(ReleaseLifecycleService):
    """Stateful lifecycle stand-in that toggles paused releases in memory."""

    is_configured = True
    paused_releases: set[str] = field(default_factory=set)

    async def pause(self, release_id: str) -> bool:
        if release_id in self.paused_releases:
            return False
        self.paused_releases.add(release_id)
        return True

    async def resume(self, release_id: str) -> bool:
        if release_id not in self.paused_releases:
            return False
        self.paused_releases.remove(release_id)
        return True


@dataclass(slots=True)
class InMemoryReleaseSearchService(ReleaseSearchService):
    """Search stand-in returning pre-registered results per query."""

    is_configured = True
    _registry: dict[tuple[str, str | None], list[ReleaseSearchResultRecord]] = field(
        default_factory=dict,
    )
    _cache: dict[str, ReleaseSearchResultRecord] = field(default_factory=dict)
    _torrents: dict[str, bytes] = field(default_factory=dict)

    def register_results(
        self,
        query: str,
        *,
        request_id: str | None,
        results: list[ReleaseSearchResultRecord],
    ) -> None:
        self._registry[(query, request_id)] = list(results)
        for result in results:
            self._cache[result.release_id] = result

    async def search(
        self,
        query: str,
        request_id: str | None = None,
        indexer_id: int | None = None,
    ) -> ReleaseSearchResults:
        matches = self._registry.get((query, request_id), [])
        return ReleaseSearchResults(results=list(matches), query=query, total_results=len(matches))

    def resolve(self, release_id: str) -> ReleaseSearchResultRecord | None:
        return self._cache.get(release_id)

    def register_torrent(self, release_id: str, data: bytes) -> None:
        self._torrents[release_id] = data

    async def fetch_torrent(self, url: str) -> bytes:
        if url.startswith("memory://"):
            release_id = url.removeprefix("memory://")
            if release_id in self._torrents:
                return self._torrents[release_id]
        raise FileNotFoundError(f"Torrent data not registered for URL '{url}'")


@dataclass(slots=True)
class InMemoryReleaseDownloadService(ReleaseDownloadService):
    """Download stand-in that writes the magnet where a client would put it."""

    is_configured = True
    download_dir: Path = field(
        default_factory=lambda: Path(tempfile.gettempdir()) / "releasarr-downloads"
    )
    downloads: list[tuple[str, str, Path]] = field(default_factory=list)
    # Torrents the stand-in client knows about, keyed by upper-cased info hash.
    # A hash missing from here is one the client has never seen.
    torrents: dict[str, ReleaseTorrentState] = field(default_factory=dict)

    async def queue_download(
        self,
        request_id: str,
        release_id: str,
        magnet_link: str,
        torrent_bytes: bytes | None = None,
    ) -> QueuedDownload:
        try:
            self.download_dir.mkdir(parents=True, exist_ok=True)
            file_path = self.download_dir / f"{release_id}.torrent"
            file_path.write_text(magnet_link, encoding="utf-8")
        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeError(
                f"Failed to download torrent for release '{release_id}': {exc}"
            ) from exc

        self.downloads.append((request_id, release_id, file_path))
        details: dict[str, object] = {
            "request_id": request_id,
            "release_id": release_id,
            "file_path": str(file_path),
            "ingest_source": "magnet",
        }
        if torrent_bytes is not None:
            details["torrent_bytes_len"] = len(torrent_bytes)
        return QueuedDownload(
            operation="queue_download",
            status="completed",
            operation_id=f"download:{request_id}:{release_id}",
            location=None,
            message=None,
            resource_id=release_id,
            details=details,
        )

    async def delete_download(self, release_id: str) -> None:
        self.downloads = [entry for entry in self.downloads if entry[1] != release_id]

    async def get_torrent_state(self, info_hash: str) -> ReleaseTorrentState | None:
        return self.torrents.get(info_hash.upper())

    async def get_download_directory(self, info_hash: str) -> str | None:
        return str(self.download_dir)


__all__ = [
    "FakeMediaRequestRepository",
    "FakeRadarrService",
    "FakeSonarrService",
    "FakeTmdbService",
    "FakeTvdbService",
    "InMemoryReleaseDownloadService",
    "InMemoryReleaseLifecycleService",
    "InMemoryReleaseSearchService",
    "UnusedIndexerDirectoryCalls",
    "UnusedMediaRequestCalls",
    "UnusedRadarrLibraryCalls",
    "UnusedReleaseDownloadCalls",
    "UnusedReleaseRepositoryCalls",
    "UnusedRequestWarningCalls",
    "UnusedScheduledTaskCalls",
    "UnusedSonarrLibraryCalls",
    "UnusedSyncJobCalls",
    "UnusedTmdbSearch",
    "UnusedTvdbSearch",
    "make_movie_details",
    "make_record",
    "make_series_details",
]
