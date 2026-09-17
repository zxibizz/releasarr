"""Tests for reconciling media requests with the seasons Sonarr monitors."""

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
from src.application.interfaces.releases import ReleaseRecord
from src.application.interfaces.sonarr import (
    ManualImportFile,
    SeriesDetails,
    SeriesSeasonDetails,
    SonarrEpisode,
)
from src.application.interfaces.tvdb import TvdbSeriesMetadata, TvdbService, TvdbTranslation
from src.application.use_cases.requests.recompute_state import RecomputeRequestStateUseCase
from src.application.use_cases.requests.state import RequestStateDeriver
from src.application.use_cases.requests.sync_sonarr import SyncSonarrMediaRequestsUseCase
from src.application.utility.sentinels import UNSET
from src.domain.enums import MediaRequestStatus, MediaType, ReleaseStatus
from tests.fakes import (
    UnusedMediaRequestCalls,
    UnusedReleaseRepositoryCalls,
    UnusedSonarrLibraryCalls,
    UnusedTvdbSearch,
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
            aired_episodes=data.aired_episodes,
            downloaded_episodes=data.downloaded_episodes,
            series_title=data.series_title,
            series_year=data.series_year,
            sonarr_series_id=data.sonarr_series_id,
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


class FakeSonarrService(UnusedSonarrLibraryCalls):
    def __init__(self, library: list[SeriesDetails]) -> None:
        self._library = library
        self.series_calls: list[int] = []

    async def list_series(self) -> list[SeriesDetails]:
        return self._library

    async def get_series(self, series_id: int) -> SeriesDetails:
        self.series_calls.append(series_id)
        return next(details for details in self._library if details.id == series_id)

    async def get_episodes(self, series_id: int) -> list[SonarrEpisode]:
        return []

    async def manual_import(self, files: list[ManualImportFile]) -> bool:
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
    torrent_source: str | None = "indexer",
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
        torrent_source=torrent_source,
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


def make_series_details() -> SeriesDetails:
    return SeriesDetails(
        id=10,
        title="Example Show",
        year=2020,
        overview="A sample overview",
        poster_url="http://poster",
        imdb_id="tt1234567",
        tvdb_id=555,
        genres=["Drama"],
        seasons={
            1: SeriesSeasonDetails(
                season_number=1,
                episode_count=10,
                total_episode_count=10,
                episode_file_count=5,
                monitored=True,
            ),
            3: SeriesSeasonDetails(
                season_number=3,
                episode_count=8,
                total_episode_count=8,
                episode_file_count=0,
                monitored=True,
            ),
        },
    )


def make_existing_records() -> dict[str, MediaRequestRecord]:
    now = datetime.now(UTC)
    return {
        "req-1": MediaRequestRecord(
            id="req-1",
            media_type=MediaType.SERIES,
            status=MediaRequestStatus.COMPLETED,
            title="Old Title",
            year=2019,
            overview=None,
            poster_url=None,
            genres=["Mystery"],
            runtime_minutes=None,
            imdb_id="tt0000001",
            season_number=1,
            total_episodes=5,
            series_title="Legacy",
            series_year=2019,
            sonarr_series_id=10,
            created_at=now,
            updated_at=now,
            localizations={},
        ),
        "req-2": MediaRequestRecord(
            id="req-2",
            media_type=MediaType.SERIES,
            status=MediaRequestStatus.SEARCHING,
            title="Another Title",
            year=2018,
            overview=None,
            poster_url=None,
            genres=[],
            runtime_minutes=None,
            imdb_id=None,
            season_number=2,
            total_episodes=6,
            aired_episodes=6,
            series_title="Legacy",
            series_year=2018,
            sonarr_series_id=10,
            created_at=now,
            updated_at=now,
            localizations={},
        ),
    }


class FakeTvdbService(UnusedTvdbSearch, TvdbService):
    def __init__(
        self,
        metadata: dict[int, TvdbSeriesMetadata] | None = None,
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

    async def get_series(
        self,
        tvdb_id: int,
        languages: Sequence[str] | None = None,
    ) -> TvdbSeriesMetadata:
        langs = () if languages is None else tuple(languages)
        self.calls.append((tvdb_id, langs))
        return self._metadata[tvdb_id]


@pytest.mark.asyncio
async def test_sync_sonarr_creates_updates_and_prunes() -> None:
    repository = FakeMediaRequestRepository(records=make_existing_records())
    sonarr = FakeSonarrService([make_series_details()])
    tvdb_metadata = TvdbSeriesMetadata(
        tvdb_id=555,
        name="Example Show",
        overview="Default TVDB overview",
        image_url="http://tvdb/poster",
        year=2020,
        genres=["Drama"],
        translations={
            "eng": TvdbTranslation(
                language="eng",
                title="Example Show",
                overview="English overview",
                season_overviews={1: "English season one", 3: "English season three"},
            ),
            "rus": TvdbTranslation(
                language="rus",
                title="Пример шоу",
                overview="Русское описание",
                season_overviews={1: "Русский сезон один", 3: "Русский сезон три"},
            ),
        },
    )
    tvdb = FakeTvdbService(metadata={555: tvdb_metadata})

    use_case = SyncSonarrMediaRequestsUseCase(
        repository=repository,
        sonarr_service=sonarr,
        tvdb_service=tvdb,
        recompute_state=make_recompute(repository),
        metadata_languages=("rus", "eng"),
    )
    result = await use_case.execute()

    assert (result.created, result.updated, result.deleted) == (1, 1, 1)

    # Season 1 is still monitored, so it is refreshed and reopened for the
    # episodes Sonarr has no file for.
    season_one = await repository.find_by_sonarr(sonarr_series_id=10, season_number=1)
    assert season_one is not None
    assert season_one.status == MediaRequestStatus.PENDING
    assert season_one.title == "Пример шоу - Season 1"
    assert season_one.total_episodes == 10
    assert season_one.imdb_id == "tt1234567"
    assert season_one.poster_url == "http://poster"
    assert "rus" in season_one.localizations
    assert season_one.localizations["rus"].title == "Пример шоу"
    assert season_one.localizations["eng"].title == "Example Show"
    assert season_one.localizations["rus"].overview == "Русский сезон один"
    assert season_one.localizations["eng"].overview == "English season one"
    # Sonarr's season statistics, kept so the card can derive the counts without
    # another round trip.
    assert (season_one.aired_episodes, season_one.downloaded_episodes) == (10, 5)

    # Season 2 is no longer monitored, so its request goes with the monitoring.
    assert await repository.find_by_sonarr(sonarr_series_id=10, season_number=2) is None

    # Season 3 is newly monitored, so it gets a request.
    season_three = await repository.find_by_sonarr(sonarr_series_id=10, season_number=3)
    assert season_three is not None
    assert season_three.status == MediaRequestStatus.PENDING
    assert season_three.title == "Пример шоу - Season 3"
    assert (season_three.aired_episodes, season_three.downloaded_episodes) == (8, 0)
    assert season_three.series_title == "Example Show"
    assert season_three.series_year == 2020
    assert season_three.poster_url == "http://poster"
    assert season_three.localizations["eng"].overview == "English season three"
    assert season_three.localizations["rus"].overview == "Русский сезон три"

    # The created row and the refreshed row share one TVDB read per run.
    assert tvdb.calls == [(555, ("rus", "eng"))]


@pytest.mark.asyncio
async def test_sync_sonarr_logs_a_pruning_against_the_request(
    captured_records: list[dict[str, Any]],
) -> None:
    """Pruning a season is activity a user should see on the request.

    The /logs endpoint filters on request_id and the log file records at INFO, so
    a debug-level entry here would never reach the request's activity view.
    """

    records = make_existing_records()
    repository = FakeMediaRequestRepository(records={"req-2": records["req-2"]})

    use_case = SyncSonarrMediaRequestsUseCase(
        repository=repository,
        sonarr_service=FakeSonarrService([make_series_details()]),
        tvdb_service=FakeTvdbService(is_configured=False),
        recompute_state=make_recompute(repository),
    )
    await use_case.execute()

    assert await repository.find_by_sonarr(sonarr_series_id=10, season_number=2) is None
    pruned = [record for record in captured_records if record.get("request_id") == "req-2"]
    assert pruned, "pruning a season produced no log entry bound to the request"
    assert pruned[0]["level"] == "INFO"
    assert pruned[0]["season_number"] == 2


@pytest.mark.asyncio
async def test_sync_sonarr_preserves_in_flight_status() -> None:
    """A metadata refresh must not knock a downloading season back to pending.

    The sync hands the recompute a not-complete verdict, and the in-flight
    release is what keeps the request downloading.
    """

    records = make_existing_records()
    records["req-1"].status = MediaRequestStatus.DOWNLOADING
    repository = FakeMediaRequestRepository(records=records)
    sonarr = FakeSonarrService([make_series_details()])

    use_case = SyncSonarrMediaRequestsUseCase(
        repository=repository,
        sonarr_service=sonarr,
        tvdb_service=FakeTvdbService(is_configured=False),
        recompute_state=make_recompute(
            repository, releases=[make_release("rel-1", request_ids=["req-1"])]
        ),
    )
    await use_case.execute()

    season_one = await repository.find_by_sonarr(sonarr_series_id=10, season_number=1)
    assert season_one is not None
    assert season_one.status == MediaRequestStatus.DOWNLOADING
    # The rest of the metadata is still refreshed.
    assert season_one.title == "Example Show - Season 1"
    assert season_one.total_episodes == 10


def make_airing_details() -> SeriesDetails:
    """A ten-episode season Sonarr has aired and filed four of."""

    return SeriesDetails(
        id=10,
        title="Example Show",
        year=2020,
        overview=None,
        poster_url=None,
        imdb_id=None,
        tvdb_id=555,
        genres=[],
        seasons={
            1: SeriesSeasonDetails(
                season_number=1,
                episode_count=4,
                total_episode_count=10,
                episode_file_count=4,
                monitored=True,
            )
        },
    )


def make_airing_records(status: MediaRequestStatus) -> dict[str, MediaRequestRecord]:
    now = datetime.now(UTC)
    return {
        "req-1": MediaRequestRecord(
            id="req-1",
            media_type=MediaType.SERIES,
            status=status,
            title="Example Show - Season 1",
            year=2020,
            overview=None,
            poster_url=None,
            genres=[],
            runtime_minutes=None,
            imdb_id=None,
            season_number=1,
            total_episodes=10,
            aired_episodes=4,
            downloaded_episodes=4,
            series_title="Example Show",
            series_year=2020,
            sonarr_series_id=10,
            created_at=now,
            updated_at=now,
            localizations={},
        )
    }


@pytest.mark.asyncio
async def test_sync_sonarr_reopens_a_season_that_is_still_airing() -> None:
    """Every aired episode having a file is not the same as the season being over.

    Sonarr counts only aired episodes, so a running season reads as complete every
    week between airings; the verdict's has_unaired is what keeps the request open
    instead of closing and reopening it per episode. A release grabbed by hand is
    the case that cannot absorb that: nothing will re-grab it for the episodes
    that follow.
    """

    repository = FakeMediaRequestRepository(
        records=make_airing_records(MediaRequestStatus.COMPLETED)
    )
    sonarr = FakeSonarrService([make_airing_details()])

    use_case = SyncSonarrMediaRequestsUseCase(
        repository=repository,
        sonarr_service=sonarr,
        tvdb_service=FakeTvdbService(is_configured=False),
        recompute_state=make_recompute(repository),
    )
    result = await use_case.execute()

    season_one = await repository.find_by_sonarr(sonarr_series_id=10, season_number=1)
    assert season_one is not None
    assert season_one.status == MediaRequestStatus.PENDING
    assert result.deleted == 0


def make_season_details(*, aired: int, total: int, files: int) -> SeriesDetails:
    """Series 10, season 1, with Sonarr's numbers for it supplied by the test."""

    return SeriesDetails(
        id=10,
        title="Example Show",
        year=2020,
        overview=None,
        poster_url=None,
        imdb_id=None,
        tvdb_id=555,
        genres=[],
        seasons={
            1: SeriesSeasonDetails(
                season_number=1,
                episode_count=aired,
                total_episode_count=total,
                episode_file_count=files,
                monitored=True,
            )
        },
    )


def make_counted_record(
    *,
    status: MediaRequestStatus,
    total_episodes: int,
    aired_episodes: int,
    downloaded_episodes: int,
) -> MediaRequestRecord:
    now = datetime.now(UTC)
    return MediaRequestRecord(
        id="req-1",
        media_type=MediaType.SERIES,
        status=status,
        title="Example Show - Season 1",
        year=2020,
        overview=None,
        poster_url=None,
        genres=[],
        runtime_minutes=None,
        imdb_id=None,
        season_number=1,
        total_episodes=total_episodes,
        aired_episodes=aired_episodes,
        downloaded_episodes=downloaded_episodes,
        series_title="Example Show",
        series_year=2020,
        sonarr_series_id=10,
        created_at=now,
        updated_at=now,
        localizations={},
    )


@pytest.mark.asyncio
async def test_sync_sonarr_refreshes_counts_on_every_run() -> None:
    """A monitored season's counts track Sonarr's own numbers, run over run."""

    record = make_counted_record(
        status=MediaRequestStatus.MONITORING,
        total_episodes=8,
        aired_episodes=7,
        downloaded_episodes=6,
    )
    repository = FakeMediaRequestRepository(records={"req-1": record})
    details = make_season_details(aired=7, total=8, files=7)
    sonarr = FakeSonarrService([details])
    # An already-imported release the indexer could still improve on is what a
    # monitoring status rests on; without one there is nothing to monitor.
    exported = make_release(
        "rel-1",
        request_ids=["req-1"],
        status=ReleaseStatus.COMPLETED,
        last_exported_info_hash="hash",
    )

    use_case = SyncSonarrMediaRequestsUseCase(
        repository=repository,
        sonarr_service=sonarr,
        tvdb_service=FakeTvdbService(is_configured=False),
        recompute_state=make_recompute(repository, releases=[exported]),
    )
    await use_case.execute()

    assert record.downloaded_episodes == 7
    # The season is still airing, so the request stays open on the status the
    # release side gave it rather than being completed or reopened.
    assert record.status == MediaRequestStatus.MONITORING
    _, update = repository.updated[0]
    assert update.status is UNSET

    # Sonarr airs and files the last episode; the next run adopts the numbers
    # and completes the request.
    details.seasons[1].episode_count = 8
    details.seasons[1].episode_file_count = 8
    details.seasons[1].total_episode_count = 8
    await use_case.execute()

    assert (record.aired_episodes, record.downloaded_episodes) == (8, 8)
    assert record.status == MediaRequestStatus.COMPLETED


@pytest.mark.asyncio
async def test_sync_sonarr_completes_with_sonarrs_own_counts() -> None:
    """Completing a season writes the numbers Sonarr just reported for it."""

    record = make_counted_record(
        status=MediaRequestStatus.MONITORING,
        total_episodes=8,
        aired_episodes=8,
        downloaded_episodes=6,
    )
    repository = FakeMediaRequestRepository(records={"req-1": record})
    sonarr = FakeSonarrService([make_season_details(aired=8, total=8, files=8)])

    use_case = SyncSonarrMediaRequestsUseCase(
        repository=repository,
        sonarr_service=sonarr,
        tvdb_service=FakeTvdbService(is_configured=False),
        recompute_state=make_recompute(repository),
    )
    await use_case.execute()

    assert record.status == MediaRequestStatus.COMPLETED
    assert record.downloaded_episodes == 8


@pytest.mark.asyncio
async def test_sync_sonarr_leaves_an_in_flight_airing_season_alone() -> None:
    """Episodes still to air do not close a request whose release is in flight."""

    repository = FakeMediaRequestRepository(
        records=make_airing_records(MediaRequestStatus.DOWNLOADING)
    )
    sonarr = FakeSonarrService([make_airing_details()])

    use_case = SyncSonarrMediaRequestsUseCase(
        repository=repository,
        sonarr_service=sonarr,
        tvdb_service=FakeTvdbService(is_configured=False),
        recompute_state=make_recompute(
            repository, releases=[make_release("rel-1", request_ids=["req-1"])]
        ),
    )
    await use_case.execute()

    season_one = await repository.find_by_sonarr(sonarr_series_id=10, season_number=1)
    assert season_one is not None
    assert season_one.status == MediaRequestStatus.DOWNLOADING


@pytest.mark.asyncio
async def test_sync_sonarr_adopts_a_downloaded_season_as_completed() -> None:
    """A season with every aired episode filed never sat on the missing list.

    That used to mean no request at all; under the library sweep it is adopted
    and immediately reads as completed.
    """

    repository = FakeMediaRequestRepository()
    sonarr = FakeSonarrService([make_season_details(aired=10, total=10, files=10)])

    use_case = SyncSonarrMediaRequestsUseCase(
        repository=repository,
        sonarr_service=sonarr,
        tvdb_service=FakeTvdbService(is_configured=False),
        recompute_state=make_recompute(repository),
    )
    result = await use_case.execute()

    assert result.created == 1
    season_one = await repository.find_by_sonarr(sonarr_series_id=10, season_number=1)
    assert season_one is not None
    assert season_one.status == MediaRequestStatus.COMPLETED


@pytest.mark.asyncio
async def test_sync_sonarr_keeps_an_airing_season_pending() -> None:
    """Nothing aired missing today is not the same as nothing left to come."""

    repository = FakeMediaRequestRepository()
    sonarr = FakeSonarrService([make_airing_details()])

    use_case = SyncSonarrMediaRequestsUseCase(
        repository=repository,
        sonarr_service=sonarr,
        tvdb_service=FakeTvdbService(is_configured=False),
        recompute_state=make_recompute(repository),
    )
    await use_case.execute()

    season_one = await repository.find_by_sonarr(sonarr_series_id=10, season_number=1)
    assert season_one is not None
    assert season_one.status == MediaRequestStatus.PENDING


@pytest.mark.asyncio
async def test_sync_sonarr_prunes_nothing_when_the_library_answers_empty(
    captured_records: list[dict[str, Any]],
) -> None:
    """An empty answer from Sonarr reads as a restart, not as a wiped library."""

    repository = FakeMediaRequestRepository(records=make_existing_records())

    use_case = SyncSonarrMediaRequestsUseCase(
        repository=repository,
        sonarr_service=FakeSonarrService([]),
        tvdb_service=FakeTvdbService(is_configured=False),
        recompute_state=make_recompute(repository),
    )
    result = await use_case.execute()

    assert result.deleted == 0
    assert await repository.list_sonarr_requests() != []
    assert any(record.get("level") == "WARNING" for record in captured_records)


@pytest.mark.asyncio
async def test_sync_sonarr_leaves_an_unsettled_series_alone() -> None:
    """A series mid-add has season flags Sonarr is about to rewrite."""

    details = make_series_details()
    details.has_add_options = True
    repository = FakeMediaRequestRepository(records=make_existing_records())

    use_case = SyncSonarrMediaRequestsUseCase(
        repository=repository,
        sonarr_service=FakeSonarrService([details]),
        tvdb_service=FakeTvdbService(is_configured=False),
        recompute_state=make_recompute(repository),
    )
    result = await use_case.execute()

    assert (result.created, result.updated, result.deleted) == (0, 0, 0)
    assert await repository.find_by_sonarr(sonarr_series_id=10, season_number=2) is not None


@pytest.mark.asyncio
async def test_sync_sonarr_ignores_unmonitored_seasons() -> None:
    details = make_series_details()
    for season in details.seasons.values():
        season.monitored = False
    repository = FakeMediaRequestRepository()

    use_case = SyncSonarrMediaRequestsUseCase(
        repository=repository,
        sonarr_service=FakeSonarrService([details]),
        tvdb_service=FakeTvdbService(is_configured=False),
        recompute_state=make_recompute(repository),
    )
    result = await use_case.execute()

    assert (result.created, result.updated, result.deleted) == (0, 0, 0)
    assert await repository.list_sonarr_requests() == []


@pytest.mark.asyncio
async def test_sync_sonarr_assigns_a_new_season_to_the_series_owner() -> None:
    records = make_existing_records()
    records["req-1"].owner_user_id = "user-1"
    repository = FakeMediaRequestRepository(records={"req-1": records["req-1"]})

    use_case = SyncSonarrMediaRequestsUseCase(
        repository=repository,
        sonarr_service=FakeSonarrService([make_series_details()]),
        tvdb_service=FakeTvdbService(is_configured=False),
        recompute_state=make_recompute(repository),
    )
    await use_case.execute()

    season_three = await repository.find_by_sonarr(sonarr_series_id=10, season_number=3)
    assert season_three is not None
    assert season_three.owner_user_id == "user-1"


@pytest.mark.asyncio
async def test_sync_sonarr_reuses_stored_localizations() -> None:
    """TVDB is asked only for rows with nothing stored, not on every sweep."""

    records = make_existing_records()
    records["req-1"].localizations = {
        "eng": MediaLocalization(title="Example Show", overview="Stored overview")
    }
    repository = FakeMediaRequestRepository(records={"req-1": records["req-1"]})
    details = make_series_details()
    details.seasons = {1: details.seasons[1]}
    tvdb = FakeTvdbService()

    use_case = SyncSonarrMediaRequestsUseCase(
        repository=repository,
        sonarr_service=FakeSonarrService([details]),
        tvdb_service=tvdb,
        recompute_state=make_recompute(repository),
    )
    await use_case.execute()

    assert tvdb.calls == []
    season_one = await repository.find_by_sonarr(sonarr_series_id=10, season_number=1)
    assert season_one is not None
    assert season_one.localizations["eng"].overview == "Stored overview"
