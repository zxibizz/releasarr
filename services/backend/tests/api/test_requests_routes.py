"""Integration tests for media request API routes."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import status
from httpx import AsyncClient

from src.api.app import app
from src.api.routes.requests import (
    _get_create_use_case,
    _get_delete_use_case,
    _get_episodes_use_case,
    _get_get_use_case,
    _get_list_use_case,
    _get_seasons_use_case,
    _get_update_seasons_use_case,
    _get_update_use_case,
)
from src.application.use_cases.discover import (
    ListRequestSeasonsUseCase,
    SeasonOptionDTO,
    SeasonsUnmanageableError,
    SeriesSeasonsDTO,
    UpdateRequestSeasonsCommand,
    UpdateRequestSeasonsUseCase,
)
from src.application.use_cases.requests import (
    CreateMediaRequestUseCase,
    DeleteMediaRequestUseCase,
    EmptyUpdatePayloadError,
    GetMediaRequestUseCase,
    ListMediaRequestsUseCase,
    ListRequestEpisodesUseCase,
    MediaRequestNotFoundError,
    MovieRequestDTO,
    SeasonEpisodeDTO,
    SeasonEpisodesDTO,
    UpdateMediaRequestUseCase,
)
from src.application.use_cases.requests.commands import (
    ListRequestsOptions,
    UpdateMediaRequestCommand,
)
from src.application.use_cases.requests.dto import (
    MediaRequestsPageDTO,
    SeriesEpisodeCountsDTO,
    SeriesRequestDTO,
)
from src.core.container import get_container
from src.domain.enums import EpisodeStatus, MediaRequestStatus

API_KEY_HEADER = {"X-API-Key": get_container().settings.api_key.get_secret_value()}


class FakeListUseCase(ListMediaRequestsUseCase):
    def __init__(self, page: MediaRequestsPageDTO) -> None:
        self._page = page

    async def execute(self, options: ListRequestsOptions | None = None) -> MediaRequestsPageDTO:
        return self._page


class FakeCreateUseCase(CreateMediaRequestUseCase):
    def __init__(self, dto: MovieRequestDTO) -> None:
        self._dto = dto

    async def execute(self, command: Any) -> MovieRequestDTO:
        return self._dto


class FakeGetUseCase(GetMediaRequestUseCase):
    def __init__(self, dto: MovieRequestDTO | None) -> None:
        self._dto = dto

    async def execute(self, request_id: str) -> MovieRequestDTO:
        if self._dto is None:
            raise MediaRequestNotFoundError(request_id)
        return self._dto


class FakeUpdateUseCase(UpdateMediaRequestUseCase):
    def __init__(self, dto: MovieRequestDTO | None, *, raise_empty: bool = False) -> None:
        self._dto = dto
        self._raise_empty = raise_empty

    async def execute(self, request_id: str, command: UpdateMediaRequestCommand) -> MovieRequestDTO:
        if self._raise_empty:
            raise EmptyUpdatePayloadError()
        if self._dto is None:
            raise MediaRequestNotFoundError(request_id)
        return self._dto


class FakeDeleteUseCase(DeleteMediaRequestUseCase):
    def __init__(self, deleted: bool) -> None:
        self._deleted = deleted

    async def execute(self, request_id: str) -> None:
        if not self._deleted:
            raise MediaRequestNotFoundError(request_id)


class FakeSeasonsUseCase(ListRequestSeasonsUseCase):
    def __init__(self, dto: SeriesSeasonsDTO | None) -> None:
        self._dto = dto

    async def execute(self, request_id: str) -> SeriesSeasonsDTO:
        if self._dto is None:
            raise SeasonsUnmanageableError(f"Request '{request_id}' has no seasons")
        return self._dto


class FakeUpdateSeasonsUseCase(UpdateRequestSeasonsUseCase):
    def __init__(self, dto: SeriesSeasonsDTO) -> None:
        self._dto = dto
        self.commands: list[UpdateRequestSeasonsCommand] = []

    async def execute(
        self,
        request_id: str,
        command: UpdateRequestSeasonsCommand,
    ) -> SeriesSeasonsDTO:
        self.commands.append(command)
        return self._dto


class FakeEpisodesUseCase(ListRequestEpisodesUseCase):
    def __init__(self, dto: SeasonEpisodesDTO | None) -> None:
        self._dto = dto

    async def execute(self, request_id: str) -> SeasonEpisodesDTO:
        if self._dto is None:
            raise SeasonsUnmanageableError(f"Request '{request_id}' has no episodes")
        return self._dto


def make_episodes_dto() -> SeasonEpisodesDTO:
    return SeasonEpisodesDTO(
        season_number=2,
        episodes=[
            SeasonEpisodeDTO(
                episode_number=1,
                title="Pilot",
                status=EpisodeStatus.DOWNLOADED,
                air_date=datetime(2020, 3, 1, 1, 0, tzinfo=UTC),
                file_size=2_147_483_648,
            ),
            SeasonEpisodeDTO(
                episode_number=2,
                title="The Next One",
                status=EpisodeStatus.MISSING,
                air_date=datetime(2020, 3, 8, 1, 0, tzinfo=UTC),
            ),
            SeasonEpisodeDTO(
                episode_number=3,
                title="Unscheduled",
                status=EpisodeStatus.UNAIRED,
            ),
        ],
    )


def make_seasons_dto() -> SeriesSeasonsDTO:
    return SeriesSeasonsDTO(
        tvdb_id=555,
        in_library=True,
        library_id=12,
        monitor_new_seasons=True,
        seasons=[
            SeasonOptionDTO(season_number=1, monitored=True, requested=True, request_id="req-1"),
            SeasonOptionDTO(season_number=2),
        ],
    )


def make_movie_dto() -> MovieRequestDTO:
    return MovieRequestDTO(
        id="req-1",
        title="Example",
        year=2024,
        poster_url="",
        overview="",
        genres=["drama"],
        status=MediaRequestStatus.PENDING,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        runtime=120,
        imdb_id="tt1234567",
    )


def make_series_dto(
    counts: SeriesEpisodeCountsDTO | None = None,
) -> SeriesRequestDTO:
    return SeriesRequestDTO(
        id="req-2",
        title="Example Show - Season 2",
        year=2024,
        poster_url="",
        overview="",
        genres=["drama"],
        status=MediaRequestStatus.PENDING,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        season_number=2,
        total_episodes=10,
        series_title="Example Show",
        series_year=2024,
        imdb_id="tt1234567",
        sonarr_series_id=12,
        episode_counts=counts,
    )


@contextmanager
def override_dependency(dep: Callable[..., Any], value: Any):
    app.dependency_overrides[dep] = lambda: value
    try:
        yield
    finally:
        app.dependency_overrides.pop(dep, None)


@pytest.mark.asyncio
async def test_list_requests_returns_results(api_client: AsyncClient) -> None:
    dto = make_movie_dto()
    page = MediaRequestsPageDTO(requests=[dto], total=1, page=1, per_page=20)
    with override_dependency(_get_list_use_case, FakeListUseCase(page)):
        response = await api_client.get("/requests", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["total"] == 1
    assert payload["requests"][0]["id"] == dto.id


@pytest.mark.asyncio
async def test_list_requests_serialises_the_episode_counts(api_client: AsyncClient) -> None:
    dto = make_series_dto(SeriesEpisodeCountsDTO(downloaded=3, pending=5, unaired=2))
    page = MediaRequestsPageDTO(requests=[dto], total=1, page=1, per_page=20)
    with override_dependency(_get_list_use_case, FakeListUseCase(page)):
        response = await api_client.get("/requests", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["requests"][0]["episode_counts"] == {
        "downloaded": 3,
        "pending": 5,
        "unaired": 2,
    }


@pytest.mark.asyncio
async def test_list_requests_reports_no_counts_for_an_unsynced_season(
    api_client: AsyncClient,
) -> None:
    """A season the sync has not filled in yet must stay distinguishable from
    one that is genuinely fully downloaded."""

    dto = make_series_dto()
    page = MediaRequestsPageDTO(requests=[dto], total=1, page=1, per_page=20)
    with override_dependency(_get_list_use_case, FakeListUseCase(page)):
        response = await api_client.get("/requests", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["requests"][0]["episode_counts"] is None


@pytest.mark.asyncio
async def test_list_requests_serialises_the_last_export_as_utc(
    api_client: AsyncClient,
) -> None:
    """The card renders this date, so it has to arrive in the same ISO-UTC shape
    as `created_at`, not as a naive local timestamp."""

    dto = make_series_dto()
    dto.exported_at = datetime(2026, 3, 4, 5, 6, 7, tzinfo=UTC)
    page = MediaRequestsPageDTO(requests=[dto], total=1, page=1, per_page=20)
    with override_dependency(_get_list_use_case, FakeListUseCase(page)):
        response = await api_client.get("/requests", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["requests"][0]["exported_at"] == "2026-03-04T05:06:07Z"


@pytest.mark.asyncio
async def test_list_requests_reports_a_never_exported_request_as_null(
    api_client: AsyncClient,
) -> None:
    dto = make_movie_dto()
    page = MediaRequestsPageDTO(requests=[dto], total=1, page=1, per_page=20)
    with override_dependency(_get_list_use_case, FakeListUseCase(page)):
        response = await api_client.get("/requests", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["requests"][0]["exported_at"] is None


@pytest.mark.asyncio
async def test_create_request_returns_created(api_client: AsyncClient) -> None:
    dto = make_movie_dto()
    with override_dependency(_get_create_use_case, FakeCreateUseCase(dto)):
        response = await api_client.post(
            "/requests",
            headers=API_KEY_HEADER,
            json={
                "type": "movie",
                "title": "Example",
                "year": 2024,
                "runtime": 120,
                "imdb_id": "tt1234567",
            },
        )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["id"] == dto.id


@pytest.mark.asyncio
async def test_get_request_not_found_returns_404(api_client: AsyncClient) -> None:
    with override_dependency(_get_get_use_case, FakeGetUseCase(None)):
        response = await api_client.get("/requests/unknown", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["code"] == "request_not_found"


@pytest.mark.asyncio
async def test_patch_request_empty_payload_returns_400(api_client: AsyncClient) -> None:
    with override_dependency(_get_update_use_case, FakeUpdateUseCase(None, raise_empty=True)):
        response = await api_client.patch(
            "/requests/req-1",
            headers=API_KEY_HEADER,
            json={},
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["code"] == "empty_update"


@pytest.mark.asyncio
async def test_delete_request_returns_204(api_client: AsyncClient) -> None:
    with override_dependency(_get_delete_use_case, FakeDeleteUseCase(True)):
        response = await api_client.delete("/requests/req-1", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_delete_request_not_found_returns_404(api_client: AsyncClient) -> None:
    with override_dependency(_get_delete_use_case, FakeDeleteUseCase(False)):
        response = await api_client.delete("/requests/unknown", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["code"] == "request_not_found"


@pytest.mark.asyncio
async def test_request_episodes_report_the_season_episode_by_episode(
    api_client: AsyncClient,
) -> None:
    with override_dependency(_get_episodes_use_case, FakeEpisodesUseCase(make_episodes_dto())):
        response = await api_client.get("/requests/req-1/episodes", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["season_number"] == 2
    assert [(episode["episode_number"], episode["status"]) for episode in payload["episodes"]] == [
        (1, "downloaded"),
        (2, "missing"),
        (3, "unaired"),
    ]
    assert payload["episodes"][0]["air_date"] == "2020-03-01T01:00:00Z"
    assert payload["episodes"][0]["file_size"] == 2_147_483_648
    assert payload["episodes"][2]["air_date"] is None
    assert payload["episodes"][2]["file_size"] is None


@pytest.mark.asyncio
async def test_request_episodes_report_a_request_with_none_as_a_conflict(
    api_client: AsyncClient,
) -> None:
    with override_dependency(_get_episodes_use_case, FakeEpisodesUseCase(None)):
        response = await api_client.get("/requests/req-1/episodes", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["code"] == "seasons_unmanageable"


@pytest.mark.asyncio
async def test_request_seasons_report_the_series_state(api_client: AsyncClient) -> None:
    with override_dependency(_get_seasons_use_case, FakeSeasonsUseCase(make_seasons_dto())):
        response = await api_client.get("/requests/req-1/seasons", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["monitor_new_seasons"] is True
    assert [(season["season_number"], season["requested"]) for season in payload["seasons"]] == [
        (1, True),
        (2, False),
    ]


@pytest.mark.asyncio
async def test_request_seasons_report_a_request_with_none_as_a_conflict(
    api_client: AsyncClient,
) -> None:
    with override_dependency(_get_seasons_use_case, FakeSeasonsUseCase(None)):
        response = await api_client.get("/requests/req-1/seasons", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["code"] == "seasons_unmanageable"


@pytest.mark.asyncio
async def test_updating_seasons_passes_the_selection_through(api_client: AsyncClient) -> None:
    use_case = FakeUpdateSeasonsUseCase(make_seasons_dto())
    with override_dependency(_get_update_seasons_use_case, use_case):
        response = await api_client.put(
            "/requests/req-1/seasons",
            headers=API_KEY_HEADER,
            json={"season_numbers": [2, 1], "monitor_new_seasons": True},
        )

    assert response.status_code == status.HTTP_200_OK
    assert use_case.commands == [
        UpdateRequestSeasonsCommand(season_numbers=[2, 1], monitor_new_seasons=True)
    ]


@pytest.mark.asyncio
async def test_updating_seasons_accepts_an_empty_selection(api_client: AsyncClient) -> None:
    """Withdrawing every season is a removal, not a malformed request."""

    use_case = FakeUpdateSeasonsUseCase(make_seasons_dto())
    with override_dependency(_get_update_seasons_use_case, use_case):
        response = await api_client.put(
            "/requests/req-1/seasons",
            headers=API_KEY_HEADER,
            json={"season_numbers": []},
        )

    assert response.status_code == status.HTTP_200_OK
    assert use_case.commands == [UpdateRequestSeasonsCommand()]


@pytest.mark.asyncio
async def test_missing_api_key_returns_401(api_client: AsyncClient) -> None:
    response = await api_client.get("/requests")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "code": "unauthorized",
        "message": "Invalid API key",
        "details": None,
    }
