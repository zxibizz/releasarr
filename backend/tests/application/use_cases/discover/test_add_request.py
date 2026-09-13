"""Tests for adding media to the library and turning it into requests."""

from __future__ import annotations

import pytest

from src.application.interfaces.arr import ArrQualityProfile, ArrRootFolder
from src.application.interfaces.radarr import MovieLookup
from src.application.interfaces.sonarr import SeriesLookup
from src.application.use_cases.discover.add_request import (
    AddMediaRequestCommand,
    AddMediaRequestUseCase,
)
from src.application.use_cases.discover.exceptions import (
    InvalidRootFolderError,
    MediaNotFoundError,
    NoQualityProfileError,
    SeasonSelectionError,
)
from src.application.use_cases.requests.dto import (
    MediaRequestDTO,
    MovieRequestDTO,
    SeriesRequestDTO,
)
from src.application.use_cases.requests.sync_radarr import SyncRadarrMediaRequestsUseCase
from src.application.use_cases.requests.sync_sonarr import SyncSonarrMediaRequestsUseCase
from src.domain.enums import MediaRequestStatus, MediaType
from tests.fakes import (
    FakeMediaRequestRepository,
    FakeRadarrService,
    FakeSonarrService,
    make_movie_details,
    make_record,
    make_series_details,
)


def build_use_case(
    *,
    repository: FakeMediaRequestRepository,
    sonarr: FakeSonarrService,
    radarr: FakeRadarrService,
    sonarr_quality_profile_id: int | None = None,
    radarr_quality_profile_id: int | None = None,
) -> AddMediaRequestUseCase:
    """Wire the real sync use cases in, so the inline request creation is covered."""

    return AddMediaRequestUseCase(
        repository=repository,
        sonarr_service=sonarr,
        radarr_service=radarr,
        sync_sonarr=SyncSonarrMediaRequestsUseCase(
            repository=repository,
            sonarr_service=sonarr,
            tvdb_service=None,
        ),
        sync_radarr=SyncRadarrMediaRequestsUseCase(
            repository=repository,
            radarr_service=radarr,
            tmdb_service=None,
        ),
        sonarr_quality_profile_id=sonarr_quality_profile_id,
        radarr_quality_profile_id=radarr_quality_profile_id,
    )


def as_series(requests: list[MediaRequestDTO]) -> list[SeriesRequestDTO]:
    assert all(isinstance(request, SeriesRequestDTO) for request in requests)
    return [request for request in requests if isinstance(request, SeriesRequestDTO)]


def as_movies(requests: list[MediaRequestDTO]) -> list[MovieRequestDTO]:
    assert all(isinstance(request, MovieRequestDTO) for request in requests)
    return [request for request in requests if isinstance(request, MovieRequestDTO)]


def series_sonarr(
    *,
    existing_series_id: int | None = None,
    season_numbers: list[int] | None = None,
    **kwargs: object,
) -> FakeSonarrService:
    return FakeSonarrService(
        lookups={
            555: SeriesLookup(
                tvdb_id=555,
                title="Example Show",
                year=2020,
                existing_series_id=existing_series_id,
                season_numbers=season_numbers if season_numbers is not None else [1, 2, 3],
            )
        },
        catalogue={12: make_series_details(12, seasons={1: (10, True), 2: (8, True)})},
        **kwargs,  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_adding_a_new_series_creates_a_request_per_season() -> None:
    repository = FakeMediaRequestRepository()
    sonarr = series_sonarr()

    requests = await build_use_case(
        repository=repository,
        sonarr=sonarr,
        radarr=FakeRadarrService(),
    ).execute(
        AddMediaRequestCommand(
            media_type=MediaType.SERIES,
            provider_id=555,
            root_folder_path="/tv",
            season_numbers=[2, 1],
        )
    )

    assert sonarr.added == [
        {
            "tvdb_id": 555,
            "root_folder_path": "/tv",
            "quality_profile_id": 4,
            "monitored_seasons": [1, 2],
            "monitor_new_seasons": False,
        }
    ]
    # The requests must exist by the time the call returns, not after a poll.
    seasons = as_series(requests)
    assert [(request.season_number, request.title) for request in seasons] == [
        (1, "Example Show - Season 1"),
        (2, "Example Show - Season 2"),
    ]
    assert all(request.status == MediaRequestStatus.PENDING for request in seasons)
    assert seasons[0].total_episodes == 10


@pytest.mark.asyncio
async def test_a_series_already_in_the_library_is_monitored_rather_than_added() -> None:
    repository = FakeMediaRequestRepository()
    sonarr = series_sonarr(existing_series_id=12)

    requests = await build_use_case(
        repository=repository,
        sonarr=sonarr,
        radarr=FakeRadarrService(),
    ).execute(
        AddMediaRequestCommand(
            media_type=MediaType.SERIES,
            provider_id=555,
            root_folder_path="/tv",
            season_numbers=[2],
        )
    )

    assert sonarr.added == []
    assert sonarr.monitored == [
        {"series_id": 12, "monitor": [2], "unmonitor": [], "monitor_new_seasons": False}
    ]
    assert [request.season_number for request in as_series(requests)] == [2]


@pytest.mark.asyncio
async def test_requesting_a_season_that_already_has_a_request_refreshes_it() -> None:
    repository = FakeMediaRequestRepository(
        records={"req-1": make_record("req-1", season_number=1, sonarr_series_id=12)}
    )

    requests = await build_use_case(
        repository=repository,
        sonarr=series_sonarr(existing_series_id=12),
        radarr=FakeRadarrService(),
    ).execute(
        AddMediaRequestCommand(
            media_type=MediaType.SERIES,
            provider_id=555,
            root_folder_path="/tv",
            season_numbers=[1],
        )
    )

    assert repository.created == []
    assert [request.id for request in requests] == ["req-1"]


@pytest.mark.asyncio
async def test_a_completed_request_is_reopened_when_requested_again() -> None:
    repository = FakeMediaRequestRepository(
        records={
            "req-1": make_record(
                "req-1",
                season_number=1,
                sonarr_series_id=12,
                status=MediaRequestStatus.COMPLETED,
            )
        }
    )

    requests = await build_use_case(
        repository=repository,
        sonarr=series_sonarr(existing_series_id=12),
        radarr=FakeRadarrService(),
    ).execute(
        AddMediaRequestCommand(
            media_type=MediaType.SERIES,
            provider_id=555,
            root_folder_path="/tv",
            season_numbers=[1],
        )
    )

    assert requests[0].status == MediaRequestStatus.PENDING


@pytest.mark.asyncio
async def test_episodes_are_awaited_before_the_request_records_their_count() -> None:
    """A just-added series has no episodes yet, which would store a count of zero."""

    sonarr = series_sonarr()

    await build_use_case(
        repository=FakeMediaRequestRepository(),
        sonarr=sonarr,
        radarr=FakeRadarrService(),
    ).execute(
        AddMediaRequestCommand(
            media_type=MediaType.SERIES,
            provider_id=555,
            root_folder_path="/tv",
            season_numbers=[1],
        )
    )

    assert sonarr.waited == [(12, [1])]


@pytest.mark.asyncio
async def test_a_series_needs_at_least_one_season() -> None:
    with pytest.raises(SeasonSelectionError):
        await build_use_case(
            repository=FakeMediaRequestRepository(),
            sonarr=series_sonarr(),
            radarr=FakeRadarrService(),
        ).execute(
            AddMediaRequestCommand(
                media_type=MediaType.SERIES,
                provider_id=555,
                root_folder_path="/tv",
                season_numbers=[],
            )
        )


@pytest.mark.asyncio
async def test_a_season_the_series_does_not_have_is_rejected() -> None:
    with pytest.raises(SeasonSelectionError) as excinfo:
        await build_use_case(
            repository=FakeMediaRequestRepository(),
            sonarr=series_sonarr(season_numbers=[1, 2]),
            radarr=FakeRadarrService(),
        ).execute(
            AddMediaRequestCommand(
                media_type=MediaType.SERIES,
                provider_id=555,
                root_folder_path="/tv",
                season_numbers=[9],
            )
        )

    assert "season 9" in str(excinfo.value)


@pytest.mark.asyncio
async def test_a_season_is_accepted_when_the_lookup_reports_none_at_all() -> None:
    """Sonarr omits seasons for some series, and refusing every season is worse."""

    sonarr = series_sonarr(season_numbers=[])

    requests = await build_use_case(
        repository=FakeMediaRequestRepository(),
        sonarr=sonarr,
        radarr=FakeRadarrService(),
    ).execute(
        AddMediaRequestCommand(
            media_type=MediaType.SERIES,
            provider_id=555,
            root_folder_path="/tv",
            season_numbers=[1],
        )
    )

    assert sonarr.added[0]["monitored_seasons"] == [1]
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_a_series_sonarr_cannot_resolve_is_reported_as_missing() -> None:
    with pytest.raises(MediaNotFoundError):
        await build_use_case(
            repository=FakeMediaRequestRepository(),
            sonarr=FakeSonarrService(),
            radarr=FakeRadarrService(),
        ).execute(
            AddMediaRequestCommand(
                media_type=MediaType.SERIES,
                provider_id=555,
                root_folder_path="/tv",
                season_numbers=[1],
            )
        )


@pytest.mark.asyncio
async def test_a_root_folder_sonarr_does_not_offer_is_rejected() -> None:
    sonarr = series_sonarr()

    with pytest.raises(InvalidRootFolderError):
        await build_use_case(
            repository=FakeMediaRequestRepository(),
            sonarr=sonarr,
            radarr=FakeRadarrService(),
        ).execute(
            AddMediaRequestCommand(
                media_type=MediaType.SERIES,
                provider_id=555,
                root_folder_path="/somewhere-else",
                season_numbers=[1],
            )
        )

    assert sonarr.added == []


@pytest.mark.asyncio
async def test_the_root_folder_is_not_checked_for_a_series_already_added() -> None:
    """Sonarr owns the path of a series it already holds."""

    sonarr = series_sonarr(existing_series_id=12)

    requests = await build_use_case(
        repository=FakeMediaRequestRepository(),
        sonarr=sonarr,
        radarr=FakeRadarrService(),
    ).execute(
        AddMediaRequestCommand(
            media_type=MediaType.SERIES,
            provider_id=555,
            root_folder_path="",
            season_numbers=[1],
        )
    )

    assert len(requests) == 1


@pytest.mark.asyncio
async def test_a_configured_quality_profile_is_used_verbatim() -> None:
    sonarr = series_sonarr(quality_profiles=[ArrQualityProfile(id=4, name="Any")])

    await build_use_case(
        repository=FakeMediaRequestRepository(),
        sonarr=sonarr,
        radarr=FakeRadarrService(),
        sonarr_quality_profile_id=7,
    ).execute(
        AddMediaRequestCommand(
            media_type=MediaType.SERIES,
            provider_id=555,
            root_folder_path="/tv",
            season_numbers=[1],
        )
    )

    assert sonarr.added[0]["quality_profile_id"] == 7


@pytest.mark.asyncio
async def test_adding_without_any_quality_profile_is_reported() -> None:
    """Both *arr apps refuse an add without a profile, so this cannot be defaulted."""

    with pytest.raises(NoQualityProfileError):
        await build_use_case(
            repository=FakeMediaRequestRepository(),
            sonarr=series_sonarr(quality_profiles=[]),
            radarr=FakeRadarrService(),
        ).execute(
            AddMediaRequestCommand(
                media_type=MediaType.SERIES,
                provider_id=555,
                root_folder_path="/tv",
                season_numbers=[1],
            )
        )


@pytest.mark.asyncio
async def test_adding_a_new_movie_creates_its_request() -> None:
    repository = FakeMediaRequestRepository()
    radarr = FakeRadarrService(
        lookups={777: MovieLookup(tmdb_id=777, title="Example Movie", year=2021)},
        catalogue={31: make_movie_details(31)},
        root_folders=[ArrRootFolder(path="/movies", free_space=2048)],
    )

    requests = await build_use_case(
        repository=repository,
        sonarr=FakeSonarrService(),
        radarr=radarr,
    ).execute(
        AddMediaRequestCommand(
            media_type=MediaType.MOVIE,
            provider_id=777,
            root_folder_path="/movies",
        )
    )

    assert radarr.added == [
        {"tmdb_id": 777, "root_folder_path": "/movies", "quality_profile_id": 2}
    ]
    movies = as_movies(requests)
    assert [(request.title, request.type) for request in movies] == [
        ("Example Movie", MediaType.MOVIE)
    ]
    assert movies[0].runtime == 116


@pytest.mark.asyncio
async def test_a_movie_already_in_the_library_is_monitored_rather_than_added() -> None:
    radarr = FakeRadarrService(
        lookups={777: MovieLookup(tmdb_id=777, title="Example Movie", existing_movie_id=31)},
        catalogue={31: make_movie_details(31)},
    )

    requests = await build_use_case(
        repository=FakeMediaRequestRepository(),
        sonarr=FakeSonarrService(),
        radarr=radarr,
    ).execute(
        AddMediaRequestCommand(
            media_type=MediaType.MOVIE,
            provider_id=777,
            root_folder_path="/movies",
        )
    )

    assert radarr.added == []
    assert radarr.monitored == [(31, True)]
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_a_movie_cannot_carry_seasons() -> None:
    with pytest.raises(SeasonSelectionError):
        await build_use_case(
            repository=FakeMediaRequestRepository(),
            sonarr=FakeSonarrService(),
            radarr=FakeRadarrService(),
        ).execute(
            AddMediaRequestCommand(
                media_type=MediaType.MOVIE,
                provider_id=777,
                root_folder_path="/movies",
                season_numbers=[1],
            )
        )


@pytest.mark.asyncio
async def test_a_movie_radarr_cannot_resolve_is_reported_as_missing() -> None:
    with pytest.raises(MediaNotFoundError):
        await build_use_case(
            repository=FakeMediaRequestRepository(),
            sonarr=FakeSonarrService(),
            radarr=FakeRadarrService(),
        ).execute(
            AddMediaRequestCommand(
                media_type=MediaType.MOVIE,
                provider_id=777,
                root_folder_path="/movies",
            )
        )
