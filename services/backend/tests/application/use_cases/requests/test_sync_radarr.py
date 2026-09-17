"""Tests for reconciling media requests with the movies Radarr monitors."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import fields
from datetime import UTC, datetime
from typing import Any

import pytest

from src.application.interfaces.media_requests import (
    CreateMediaRequestData,
    MediaLocalization,
    MediaRequestRecord,
    MediaRequestRepository,
    UpdateMediaRequestData,
)
from src.application.interfaces.radarr import MovieDetails, MovieImportFile
from src.application.interfaces.releases import ReleaseRecord
from src.application.interfaces.tmdb import TmdbMovieMetadata, TmdbService, TmdbTranslation
from src.application.use_cases.requests.recompute_state import RecomputeRequestStateUseCase
from src.application.use_cases.requests.state import RequestStateDeriver
from src.application.use_cases.requests.sync_radarr import SyncRadarrMediaRequestsUseCase
from src.application.utility.sentinels import UNSET
from src.domain.enums import MediaRequestStatus, MediaType, ReleaseStatus
from tests.fakes import (
    UnusedMediaRequestCalls,
    UnusedRadarrLibraryCalls,
    UnusedReleaseRepositoryCalls,
    UnusedTmdbSearch,
)


class FakeMediaRequestRepository(UnusedMediaRequestCalls, MediaRequestRepository):
    def __init__(self, records: dict[str, MediaRequestRecord] | None = None) -> None:
        self.records = records or {}
        self.created: list[CreateMediaRequestData] = []
        self.updated: list[tuple[str, UpdateMediaRequestData]] = []

    async def list_requests(
        self, *args: Any, **kwargs: Any
    ) -> tuple[list[MediaRequestRecord], int]:
        raise NotImplementedError

    async def create_request(self, data: CreateMediaRequestData) -> MediaRequestRecord:
        self.created.append(data)
        record = MediaRequestRecord(
            id=data.id,
            media_type=data.media_type,
            status=data.status,
            title=data.title,
            year=data.year,
            overview=data.overview,
            poster_url=data.poster_url,
            genres=list(data.genres),
            runtime_minutes=data.runtime_minutes,
            imdb_id=data.imdb_id,
            season_number=data.season_number,
            total_episodes=data.total_episodes,
            series_title=data.series_title,
            series_year=data.series_year,
            sonarr_series_id=data.sonarr_series_id,
            radarr_movie_id=data.radarr_movie_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            localizations=data.localizations,
            owner_user_id=data.owner_user_id,
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
        self.updated.append((request_id, data))
        for field in fields(UpdateMediaRequestData):
            value = getattr(data, field.name)
            if value is UNSET:
                continue
            setattr(record, field.name, value)
        record.updated_at = datetime.now(UTC)
        return record

    async def delete_request(self, request_id: str) -> bool:
        return self.records.pop(request_id, None) is not None

    async def find_by_radarr(self, *, radarr_movie_id: int) -> MediaRequestRecord | None:
        for record in self.records.values():
            if record.radarr_movie_id == radarr_movie_id:
                return record
        return None

    async def list_radarr_requests(self) -> list[MediaRequestRecord]:
        return [record for record in self.records.values() if record.radarr_movie_id is not None]


class FakeRadarrService(UnusedRadarrLibraryCalls):
    def __init__(self, library: list[MovieDetails]) -> None:
        self._library = library

    async def list_movies(self) -> list[MovieDetails]:
        return self._library

    async def get_movie(self, movie_id: int) -> MovieDetails:
        return next(movie for movie in self._library if movie.id == movie_id)

    async def manual_import(self, files: list[MovieImportFile]) -> bool:
        return True


class FakeReleaseRepository(UnusedReleaseRepositoryCalls):
    """Serves the release set the deriver sees for `get_releases_for_requests`."""

    def __init__(self, releases: list[ReleaseRecord] | None = None) -> None:
        self._releases = releases or []

    async def get_releases_for_requests(self, request_ids: list[str]) -> list[ReleaseRecord]:
        wanted = set(request_ids)
        return [release for release in self._releases if wanted & set(release.request_ids)]


class FakeWarningSynchronizer:
    async def sync_for_requests(self, request_ids: list[str]) -> None:
        pass


def make_release(
    release_id: str,
    *,
    request_ids: list[str],
    status: ReleaseStatus = ReleaseStatus.DOWNLOADING,
    info_hash: str = "hash",
    last_exported_info_hash: str | None = None,
) -> ReleaseRecord:
    return ReleaseRecord(
        id=release_id,
        name=release_id,
        info_hash=info_hash,
        size_bytes=1024,
        status=status,
        progress=0.0,
        download_speed=0.0,
        upload_speed=0.0,
        seeders=0,
        leechers=0,
        ratio=0.0,
        added_at=datetime.now(UTC),
        completed_at=None,
        request_ids=request_ids,
        requests=[],
        torrent_source="indexer",
        quality="1080p",
        files=[],
        last_exported_info_hash=last_exported_info_hash,
        export_failures_count=0,
    )


def make_recompute(
    repository: FakeMediaRequestRepository,
    releases: list[ReleaseRecord] | None = None,
) -> RecomputeRequestStateUseCase:
    """The real recompute, so the tests cover what the syncs hand it, not a fake."""

    return RecomputeRequestStateUseCase(
        repository=repository,
        release_repository=FakeReleaseRepository(releases),
        warning_synchronizer=FakeWarningSynchronizer(),  # type: ignore[arg-type]
        deriver=RequestStateDeriver(),
    )


class FakeTmdbService(UnusedTmdbSearch, TmdbService):
    def __init__(
        self,
        metadata: dict[int, TmdbMovieMetadata] | None = None,
        *,
        is_configured: bool = True,
    ) -> None:
        self._metadata = metadata or {}
        self._is_configured = is_configured
        self.calls: list[tuple[int, tuple[str, ...]]] = []

    @property
    def is_configured(self) -> bool:
        # Declared as a property on the protocol, so an instance attribute
        # cannot shadow it.
        return self._is_configured

    async def get_movie(
        self,
        tmdb_id: int,
        languages: Sequence[str] | None = None,
    ) -> TmdbMovieMetadata:
        self.calls.append((tmdb_id, () if languages is None else tuple(languages)))
        return self._metadata[tmdb_id]


def make_movie(
    movie_id: int = 156,
    title: str = "Arrival",
    *,
    monitored: bool = True,
    has_file: bool = False,
) -> MovieDetails:
    return MovieDetails(
        id=movie_id,
        title=title,
        year=2016,
        overview="Linguist meets heptapods.",
        poster_url="http://poster",
        imdb_id="tt2543164",
        tmdb_id=329865,
        genres=["Drama"],
        runtime_minutes=116,
        has_file=has_file,
        monitored=monitored,
    )


def make_record(
    request_id: str,
    radarr_movie_id: int,
    status: MediaRequestStatus,
) -> MediaRequestRecord:
    now = datetime.now(UTC)
    return MediaRequestRecord(
        id=request_id,
        media_type=MediaType.MOVIE,
        status=status,
        title="Old Title",
        year=2015,
        overview=None,
        poster_url=None,
        genres=[],
        runtime_minutes=None,
        imdb_id=None,
        season_number=None,
        total_episodes=None,
        series_title=None,
        series_year=None,
        radarr_movie_id=radarr_movie_id,
        created_at=now,
        updated_at=now,
        localizations={},
    )


@pytest.mark.asyncio
async def test_sync_radarr_creates_updates_and_prunes() -> None:
    repository = FakeMediaRequestRepository(
        records={
            # Still monitored and fileless, so it is refreshed and reopened.
            "req-1": make_record("req-1", 156, MediaRequestStatus.COMPLETED),
            # No longer monitored, so its request goes with the monitoring.
            "req-2": make_record("req-2", 999, MediaRequestStatus.PENDING),
        }
    )
    radarr = FakeRadarrService([make_movie(), make_movie(200, "Dune")])
    tmdb = FakeTmdbService(
        metadata={
            329865: TmdbMovieMetadata(
                tmdb_id=329865,
                translations={
                    "eng": TmdbTranslation(
                        language="eng",
                        title="Arrival",
                        overview="English overview",
                    ),
                    "rus": TmdbTranslation(
                        language="rus",
                        title="Прибытие",
                        overview="Русское описание",
                    ),
                },
            )
        }
    )

    use_case = SyncRadarrMediaRequestsUseCase(
        repository=repository,
        radarr_service=radarr,
        tmdb_service=tmdb,
        recompute_state=make_recompute(repository),
        metadata_languages=("rus", "eng"),
    )
    result = await use_case.execute()

    assert (result.created, result.updated, result.deleted) == (1, 1, 1)

    refreshed = await repository.find_by_radarr(radarr_movie_id=156)
    assert refreshed is not None
    assert refreshed.status == MediaRequestStatus.PENDING
    assert refreshed.title == "Прибытие"
    assert refreshed.overview == "Русское описание"
    assert refreshed.runtime_minutes == 116
    assert refreshed.imdb_id == "tt2543164"
    assert refreshed.localizations["eng"].title == "Arrival"

    assert await repository.find_by_radarr(radarr_movie_id=999) is None

    created = await repository.find_by_radarr(radarr_movie_id=200)
    assert created is not None
    assert created.media_type == MediaType.MOVIE
    # The check constraint on media_requests rejects a movie carrying season fields.
    assert created.season_number is None
    assert created.total_episodes is None

    # The created row and the refreshed row share one TMDB read per run.
    assert tmdb.calls == [(329865, ("rus", "eng"))]


@pytest.mark.asyncio
async def test_sync_radarr_logs_a_pruning_against_the_request(
    captured_records: list[dict[str, Any]],
) -> None:
    """Pruning a movie is activity a user should see on the request.

    The /logs endpoint filters on request_id and the log file records at INFO, so
    a debug-level entry here would never reach the request's activity view.
    """

    repository = FakeMediaRequestRepository(
        records={"req-1": make_record("req-1", 999, MediaRequestStatus.PENDING)}
    )

    use_case = SyncRadarrMediaRequestsUseCase(
        repository=repository,
        radarr_service=FakeRadarrService([make_movie()]),
        tmdb_service=FakeTmdbService(is_configured=False),
        recompute_state=make_recompute(repository),
    )
    await use_case.execute()

    assert await repository.find_by_radarr(radarr_movie_id=999) is None
    pruned = [record for record in captured_records if record.get("request_id") == "req-1"]
    assert pruned, "pruning a movie produced no log entry bound to the request"
    assert pruned[0]["level"] == "INFO"
    assert pruned[0]["radarr_movie_id"] == 999


@pytest.mark.asyncio
async def test_sync_radarr_keeps_routine_refreshes_out_of_the_activity_view(
    captured_records: list[dict[str, Any]],
) -> None:
    """A metadata refresh runs for every request on every sync, so it stays at debug."""

    repository = FakeMediaRequestRepository(
        records={"req-1": make_record("req-1", 156, MediaRequestStatus.PENDING)}
    )

    use_case = SyncRadarrMediaRequestsUseCase(
        repository=repository,
        radarr_service=FakeRadarrService([make_movie()]),
        tmdb_service=FakeTmdbService(is_configured=False),
        recompute_state=make_recompute(repository),
    )
    await use_case.execute()

    assert [record for record in captured_records if record.get("request_id") == "req-1"] == []


@pytest.mark.asyncio
async def test_sync_radarr_preserves_in_flight_status() -> None:
    """A metadata refresh must not knock a downloading movie back to pending.

    The sync hands the recompute a not-complete verdict, and the in-flight
    release is what keeps the request downloading.
    """

    repository = FakeMediaRequestRepository(
        records={"req-1": make_record("req-1", 156, MediaRequestStatus.DOWNLOADING)}
    )

    use_case = SyncRadarrMediaRequestsUseCase(
        repository=repository,
        radarr_service=FakeRadarrService([make_movie()]),
        tmdb_service=FakeTmdbService(is_configured=False),
        recompute_state=make_recompute(
            repository, releases=[make_release("rel-1", request_ids=["req-1"])]
        ),
    )
    await use_case.execute()

    record = await repository.find_by_radarr(radarr_movie_id=156)
    assert record is not None
    assert record.status == MediaRequestStatus.DOWNLOADING
    # The rest of the metadata is still refreshed.
    assert record.title == "Arrival"
    assert record.runtime_minutes == 116


@pytest.mark.asyncio
async def test_sync_radarr_falls_back_to_radarr_metadata_without_tmdb() -> None:
    """Radarr's own title still has to land under the default language."""

    repository = FakeMediaRequestRepository()

    use_case = SyncRadarrMediaRequestsUseCase(
        repository=repository,
        radarr_service=FakeRadarrService([make_movie()]),
        tmdb_service=FakeTmdbService(is_configured=False),
        recompute_state=make_recompute(repository),
        metadata_languages=("rus", "eng"),
    )
    await use_case.execute()

    record = await repository.find_by_radarr(radarr_movie_id=156)
    assert record is not None
    assert record.title == "Arrival"
    assert record.localizations["eng"].title == "Arrival"
    assert record.localizations["eng"].overview == "Linguist meets heptapods."


@pytest.mark.asyncio
async def test_sync_radarr_adopts_a_downloaded_movie_as_completed() -> None:
    """A movie Radarr already holds never sat on the missing list either."""

    repository = FakeMediaRequestRepository()

    use_case = SyncRadarrMediaRequestsUseCase(
        repository=repository,
        radarr_service=FakeRadarrService([make_movie(has_file=True)]),
        tmdb_service=FakeTmdbService(is_configured=False),
        recompute_state=make_recompute(repository),
    )
    result = await use_case.execute()

    assert result.created == 1
    record = await repository.find_by_radarr(radarr_movie_id=156)
    assert record is not None
    assert record.status == MediaRequestStatus.COMPLETED


@pytest.mark.asyncio
async def test_sync_radarr_ignores_unmonitored_movies() -> None:
    repository = FakeMediaRequestRepository(
        records={"req-1": make_record("req-1", 156, MediaRequestStatus.PENDING)}
    )

    use_case = SyncRadarrMediaRequestsUseCase(
        repository=repository,
        radarr_service=FakeRadarrService([make_movie(monitored=False)]),
        tmdb_service=FakeTmdbService(is_configured=False),
        recompute_state=make_recompute(repository),
    )
    result = await use_case.execute()

    assert (result.created, result.updated, result.deleted) == (0, 0, 1)
    assert await repository.find_by_radarr(radarr_movie_id=156) is None


@pytest.mark.asyncio
async def test_sync_radarr_prunes_nothing_when_the_library_answers_empty(
    captured_records: list[dict[str, Any]],
) -> None:
    """An empty answer from Radarr reads as a restart, not as a wiped library."""

    repository = FakeMediaRequestRepository(
        records={"req-1": make_record("req-1", 156, MediaRequestStatus.PENDING)}
    )

    use_case = SyncRadarrMediaRequestsUseCase(
        repository=repository,
        radarr_service=FakeRadarrService([]),
        tmdb_service=FakeTmdbService(is_configured=False),
        recompute_state=make_recompute(repository),
    )
    result = await use_case.execute()

    assert result.deleted == 0
    assert await repository.find_by_radarr(radarr_movie_id=156) is not None
    assert any(record.get("level") == "WARNING" for record in captured_records)


@pytest.mark.asyncio
async def test_sync_radarr_reuses_stored_localizations() -> None:
    """TMDB is asked only for rows with nothing stored, not on every sweep."""

    record = make_record("req-1", 156, MediaRequestStatus.PENDING)
    record.localizations = {"eng": MediaLocalization(title="Arrival", overview="Stored")}
    repository = FakeMediaRequestRepository(records={"req-1": record})
    tmdb = FakeTmdbService()

    use_case = SyncRadarrMediaRequestsUseCase(
        repository=repository,
        radarr_service=FakeRadarrService([make_movie()]),
        tmdb_service=tmdb,
        recompute_state=make_recompute(repository),
    )
    await use_case.execute()

    assert tmdb.calls == []
    refreshed = await repository.find_by_radarr(radarr_movie_id=156)
    assert refreshed is not None
    assert refreshed.localizations["eng"].overview == "Stored"
