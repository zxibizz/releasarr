"""Integration tests for media request API routes."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from src.api.app import app
from src.api.routes.requests import (
    _get_create_use_case,
    _get_delete_use_case,
    _get_get_use_case,
    _get_list_use_case,
    _get_update_use_case,
)
from src.application.use_cases.requests import (
    CreateMediaRequestUseCase,
    DeleteMediaRequestUseCase,
    EmptyUpdatePayloadError,
    GetMediaRequestUseCase,
    ListMediaRequestsUseCase,
    MediaRequestNotFoundError,
    MovieRequestDTO,
    UpdateMediaRequestUseCase,
)
from src.application.use_cases.requests.commands import (
    ListRequestsOptions,
    UpdateMediaRequestCommand,
)
from src.application.use_cases.requests.dto import MediaRequestsPageDTO
from src.core.container import get_container
from src.domain.enums import MediaRequestStatus

API_KEY_HEADER = {"X-API-Key": get_container().settings.api_key}


class FakeListUseCase(ListMediaRequestsUseCase):  # type: ignore[misc]
    def __init__(self, page: MediaRequestsPageDTO) -> None:
        self._page = page

    async def execute(self, options: ListRequestsOptions | None = None) -> MediaRequestsPageDTO:  # type: ignore[override]
        return self._page


class FakeCreateUseCase(CreateMediaRequestUseCase):  # type: ignore[misc]
    def __init__(self, dto: MovieRequestDTO) -> None:
        self._dto = dto

    async def execute(self, command: Any) -> MovieRequestDTO:  # type: ignore[override]
        return self._dto


class FakeGetUseCase(GetMediaRequestUseCase):  # type: ignore[misc]
    def __init__(self, dto: MovieRequestDTO | None) -> None:
        self._dto = dto

    async def execute(self, request_id: str) -> MovieRequestDTO:  # type: ignore[override]
        if self._dto is None:
            raise MediaRequestNotFoundError(request_id)
        return self._dto


class FakeUpdateUseCase(UpdateMediaRequestUseCase):  # type: ignore[misc]
    def __init__(self, dto: MovieRequestDTO | None, *, raise_empty: bool = False) -> None:
        self._dto = dto
        self._raise_empty = raise_empty

    async def execute(self, request_id: str, command: UpdateMediaRequestCommand) -> MovieRequestDTO:  # type: ignore[override]
        if self._raise_empty:
            raise EmptyUpdatePayloadError()
        if self._dto is None:
            raise MediaRequestNotFoundError(request_id)
        return self._dto


class FakeDeleteUseCase(DeleteMediaRequestUseCase):  # type: ignore[misc]
    def __init__(self, deleted: bool) -> None:
        self._deleted = deleted

    async def execute(self, request_id: str) -> bool:  # type: ignore[override]
        return self._deleted


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


@contextmanager
def override_dependency(dep: Callable[..., Any], value: Any):
    app.dependency_overrides[dep] = lambda: value
    try:
        yield
    finally:
        app.dependency_overrides.pop(dep, None)


@pytest.fixture()
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


@pytest.mark.asyncio
async def test_list_requests_returns_results(client: AsyncClient) -> None:
    dto = make_movie_dto()
    page = MediaRequestsPageDTO(requests=[dto], total=1, page=1, per_page=20)
    with override_dependency(_get_list_use_case, FakeListUseCase(page)):
        response = await client.get("/requests", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["total"] == 1
    assert payload["requests"][0]["id"] == dto.id


@pytest.mark.asyncio
async def test_create_request_returns_created(client: AsyncClient) -> None:
    dto = make_movie_dto()
    with override_dependency(_get_create_use_case, FakeCreateUseCase(dto)):
        response = await client.post(
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
async def test_get_request_not_found_returns_404(client: AsyncClient) -> None:
    with override_dependency(_get_get_use_case, FakeGetUseCase(None)):
        response = await client.get("/requests/unknown", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_patch_request_empty_payload_returns_400(client: AsyncClient) -> None:
    with override_dependency(_get_update_use_case, FakeUpdateUseCase(None, raise_empty=True)):
        response = await client.patch(
            "/requests/req-1",
            headers=API_KEY_HEADER,
            json={},
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_delete_request_returns_204(client: AsyncClient) -> None:
    with override_dependency(_get_delete_use_case, FakeDeleteUseCase(True)):
        response = await client.delete("/requests/req-1", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_missing_api_key_returns_401(client: AsyncClient) -> None:
    response = await client.get("/requests")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
