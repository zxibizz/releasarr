"""Integration tests for the discover API routes."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import status
from httpx import AsyncClient

from src.api.app import app
from src.api.dependencies.auth import get_principal
from src.api.routes.discover import (
    _add_request_use_case,
    _root_folders_use_case,
    _search_use_case,
    _season_options_use_case,
)
from src.application.use_cases.discover import (
    AddMediaRequestCommand,
    MediaSearchResultDTO,
    RootFolderDTO,
    SeasonOptionDTO,
    SeriesSeasonsDTO,
)
from src.application.use_cases.discover.exceptions import (
    InvalidRootFolderError,
    MediaNotFoundError,
    MetadataProviderUnavailableError,
    NoQualityProfileError,
    SeasonSelectionError,
)
from src.application.use_cases.requests.dto import MediaRequestDTO, SeriesRequestDTO
from src.domain.enums import MediaRequestStatus, MediaType
from src.infrastructure.http import HttpClientError

# Auth is satisfied globally by the conftest override; this header is unused
# but kept so call sites do not need touching.
API_KEY_HEADER: dict[str, str] = {}


@contextmanager
def override_dependency(dep: Callable[..., Any], value: Any):
    app.dependency_overrides[dep] = lambda: value
    try:
        yield
    finally:
        app.dependency_overrides.pop(dep, None)


class FakeSearchUseCase:
    def __init__(
        self,
        results: list[MediaSearchResultDTO] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._results = results or []
        self._error = error
        self.calls: list[tuple[str, MediaType | None, str | None]] = []

    async def execute(
        self,
        query: str,
        media_type: MediaType | None = None,
        language: str | None = None,
    ) -> list[MediaSearchResultDTO]:
        self.calls.append((query, media_type, language))
        if self._error is not None:
            raise self._error
        return self._results


class FakeSeasonOptionsUseCase:
    def __init__(self, result: SeriesSeasonsDTO | None = None, error: Exception | None = None):
        self._result = result
        self._error = error
        self.calls: list[int] = []

    async def execute(self, tvdb_id: int) -> SeriesSeasonsDTO:
        self.calls.append(tvdb_id)
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


class FakeRootFoldersUseCase:
    def __init__(self, folders: list[RootFolderDTO] | None = None, error: Exception | None = None):
        self._folders = folders or []
        self._error = error
        self.calls: list[MediaType] = []

    async def execute(
        self, media_type: MediaType, *, allowed_paths: list[str] | None = None
    ) -> list[RootFolderDTO]:
        self.calls.append(media_type)
        if self._error is not None:
            raise self._error
        return self._folders


class FakeAddRequestUseCase:
    def __init__(
        self,
        requests: Sequence[MediaRequestDTO] = (),
        error: Exception | None = None,
    ) -> None:
        self._requests = list(requests)
        self._error = error
        self.commands: list[AddMediaRequestCommand] = []

    async def execute(self, command: AddMediaRequestCommand) -> list[MediaRequestDTO]:
        self.commands.append(command)
        if self._error is not None:
            raise self._error
        return self._requests


def make_series_request(request_id: str = "req-1") -> SeriesRequestDTO:
    now = datetime.now(UTC)
    return SeriesRequestDTO(
        id=request_id,
        title="Example Show - Season 1",
        year=2020,
        poster_url="http://poster",
        overview="An overview",
        genres=["Drama"],
        status=MediaRequestStatus.PENDING,
        created_at=now,
        updated_at=now,
        season_number=1,
        total_episodes=10,
        series_title="Example Show",
        series_year=2020,
        imdb_id="tt1234567",
        sonarr_series_id=12,
    )


@pytest.mark.asyncio
async def test_search_returns_library_and_request_state(api_client: AsyncClient) -> None:
    use_case = FakeSearchUseCase(
        [
            MediaSearchResultDTO(
                media_type=MediaType.SERIES,
                provider_id=555,
                title="Example Show",
                year=2020,
                overview="An overview",
                poster_url="http://poster",
                in_library=True,
                library_id=12,
                requested_seasons=[1, 2],
                request_id="req-1",
                request_status=MediaRequestStatus.PENDING,
            )
        ]
    )

    with override_dependency(_search_use_case, use_case):
        response = await api_client.get(
            "/discover/search",
            params={"q": "example", "type": "series"},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_200_OK
    result = response.json()["results"][0]
    assert result["provider_id"] == 555
    assert result["in_library"] is True
    assert result["library_id"] == 12
    assert result["requested_seasons"] == [1, 2]
    assert result["request_status"] == "pending"
    assert use_case.calls == [("example", MediaType.SERIES, None)]


@pytest.mark.asyncio
async def test_search_without_a_type_searches_both(api_client: AsyncClient) -> None:
    use_case = FakeSearchUseCase(
        [
            MediaSearchResultDTO(
                media_type=MediaType.MOVIE,
                provider_id=42,
                title="Example Movie",
                year=2019,
                overview=None,
                poster_url=None,
                in_library=False,
                library_id=None,
            )
        ]
    )

    with override_dependency(_search_use_case, use_case):
        response = await api_client.get(
            "/discover/search",
            params={"q": "example"},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["results"][0]["type"] == "movie"
    assert use_case.calls == [("example", None, None)]


@pytest.mark.asyncio
async def test_search_forwards_the_requested_language(api_client: AsyncClient) -> None:
    use_case = FakeSearchUseCase()

    with override_dependency(_search_use_case, use_case):
        response = await api_client.get(
            "/discover/search",
            params={"q": "example", "lang": "ru"},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_200_OK
    assert use_case.calls == [("example", None, "ru")]


@pytest.mark.asyncio
async def test_search_requires_a_query(api_client: AsyncClient) -> None:
    use_case = FakeSearchUseCase()

    with override_dependency(_search_use_case, use_case):
        response = await api_client.get(
            "/discover/search",
            params={"type": "series"},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert use_case.calls == []


@pytest.mark.asyncio
async def test_search_rejects_an_unknown_media_type(api_client: AsyncClient) -> None:
    use_case = FakeSearchUseCase()

    with override_dependency(_search_use_case, use_case):
        response = await api_client.get(
            "/discover/search",
            params={"q": "example", "type": "album"},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert use_case.calls == []


@pytest.mark.asyncio
async def test_search_reports_an_unconfigured_metadata_provider(api_client: AsyncClient) -> None:
    error = MetadataProviderUnavailableError(MediaType.SERIES)

    with override_dependency(_search_use_case, FakeSearchUseCase(error=error)):
        response = await api_client.get(
            "/discover/search",
            params={"q": "example", "type": "series"},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["code"] == "metadata_provider_unavailable"


@pytest.mark.asyncio
async def test_search_reports_an_unreachable_upstream(api_client: AsyncClient) -> None:
    error = HttpClientError("connection refused")

    with override_dependency(_search_use_case, FakeSearchUseCase(error=error)):
        response = await api_client.get(
            "/discover/search",
            params={"q": "example", "type": "series"},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert response.json()["code"] == "upstream_error"


@pytest.mark.asyncio
async def test_series_seasons_returns_the_option_list(api_client: AsyncClient) -> None:
    use_case = FakeSeasonOptionsUseCase(
        SeriesSeasonsDTO(
            tvdb_id=555,
            in_library=True,
            library_id=12,
            seasons=[
                SeasonOptionDTO(
                    season_number=1,
                    monitored=True,
                    requested=True,
                    downloaded=True,
                    request_id="req-1",
                ),
                SeasonOptionDTO(season_number=2),
            ],
        )
    )

    with override_dependency(_season_options_use_case, use_case):
        response = await api_client.get("/discover/series/555/seasons", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["tvdb_id"] == 555
    assert body["in_library"] is True
    assert body["seasons"][0] == {
        "season_number": 1,
        "monitored": True,
        "requested": True,
        "downloaded": True,
        "request_id": "req-1",
    }
    assert body["seasons"][1]["requested"] is False
    assert use_case.calls == [555]


@pytest.mark.asyncio
async def test_series_seasons_reports_an_unknown_series(api_client: AsyncClient) -> None:
    error = MediaNotFoundError(MediaType.SERIES, 555)

    with override_dependency(_season_options_use_case, FakeSeasonOptionsUseCase(error=error)):
        response = await api_client.get("/discover/series/555/seasons", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["code"] == "media_not_found"


@pytest.mark.asyncio
async def test_series_seasons_rejects_a_non_numeric_id(api_client: AsyncClient) -> None:
    use_case = FakeSeasonOptionsUseCase()

    with override_dependency(_season_options_use_case, use_case):
        response = await api_client.get("/discover/series/abc/seasons", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert use_case.calls == []


@pytest.mark.asyncio
async def test_root_folders_are_scoped_to_the_media_type(api_client: AsyncClient) -> None:
    use_case = FakeRootFoldersUseCase([RootFolderDTO(path="/movies", free_space=2048)])

    with override_dependency(_root_folders_use_case, use_case):
        response = await api_client.get(
            "/discover/root-folders",
            params={"type": "movie"},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["folders"] == [{"path": "/movies", "free_space": 2048}]
    assert use_case.calls == [MediaType.MOVIE]


@pytest.mark.asyncio
async def test_adding_a_request_returns_the_created_requests(api_client: AsyncClient) -> None:
    use_case = FakeAddRequestUseCase([make_series_request()])

    with override_dependency(_add_request_use_case, use_case):
        response = await api_client.post(
            "/discover/requests",
            json={
                "type": "series",
                "provider_id": 555,
                "root_folder_path": "/tv",
                "season_numbers": [1, 2],
            },
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_201_CREATED
    request = response.json()["requests"][0]
    assert request["id"] == "req-1"
    assert request["type"] == "series"
    assert request["season_number"] == 1
    command = use_case.commands[0]
    assert command.media_type == MediaType.SERIES
    assert command.provider_id == 555
    assert command.root_folder_path == "/tv"
    assert command.season_numbers == [1, 2]


@pytest.mark.asyncio
async def test_adding_a_movie_needs_no_seasons(api_client: AsyncClient) -> None:
    use_case = FakeAddRequestUseCase()

    with override_dependency(_add_request_use_case, use_case):
        response = await api_client.post(
            "/discover/requests",
            json={"type": "movie", "provider_id": 777, "root_folder_path": "/movies"},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_201_CREATED
    assert use_case.commands[0].season_numbers == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected_status", "expected_code"),
    [
        (
            SeasonSelectionError("At least one season must be selected"),
            status.HTTP_400_BAD_REQUEST,
            "invalid_season_selection",
        ),
        (
            InvalidRootFolderError("/nope"),
            status.HTTP_400_BAD_REQUEST,
            "invalid_root_folder",
        ),
        (
            NoQualityProfileError(MediaType.SERIES),
            status.HTTP_400_BAD_REQUEST,
            "no_quality_profile",
        ),
        (
            MediaNotFoundError(MediaType.SERIES, 555),
            status.HTTP_404_NOT_FOUND,
            "media_not_found",
        ),
        (
            HttpClientError("connection refused"),
            status.HTTP_502_BAD_GATEWAY,
            "upstream_error",
        ),
    ],
)
async def test_add_request_failures_map_to_their_status(
    api_client: AsyncClient,
    error: Exception,
    expected_status: int,
    expected_code: str,
) -> None:
    with override_dependency(_add_request_use_case, FakeAddRequestUseCase(error=error)):
        response = await api_client.post(
            "/discover/requests",
            json={"type": "series", "provider_id": 555, "root_folder_path": "/tv"},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == expected_status
    assert response.json()["code"] == expected_code


@pytest.mark.asyncio
async def test_add_request_requires_a_provider_id(api_client: AsyncClient) -> None:
    use_case = FakeAddRequestUseCase()

    with override_dependency(_add_request_use_case, use_case):
        response = await api_client.post(
            "/discover/requests",
            json={"type": "series", "root_folder_path": "/tv"},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert use_case.commands == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/discover/search?q=example&type=series"),
        ("GET", "/discover/series/555/seasons"),
        ("GET", "/discover/root-folders?type=movie"),
        ("POST", "/discover/requests"),
    ],
)
async def test_discover_routes_require_an_api_key(
    api_client: AsyncClient,
    method: str,
    path: str,
) -> None:
    app.dependency_overrides.pop(get_principal, None)
    response = await api_client.request(method, path, json={})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
