"""Integration tests for release API routes."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from src.api.app import app
from src.api.routes.releases import (
    _create_use_case,
    _get_use_case,
    _list_use_case,
    _pause_use_case,
    _queue_download_use_case,
    _search_use_case,
    _update_mappings_use_case,
)
from src.application.use_cases.releases.dto import (
    AsyncOperationDTO,
    ReleaseDTO,
    ReleaseFileDTO,
    ReleaseFileMappingDTO,
    ReleaseSearchResponseDTO,
    ReleaseSearchResultDTO,
    ReleasesPageDTO,
)
from src.application.use_cases.releases.exceptions import (
    ReleaseDownloadConflictError,
    ReleaseFileNotFoundError,
    ReleaseNotFoundError,
)
from src.core.container import get_container
from src.domain.enums import ReleaseStatus

API_KEY_HEADER = {"X-API-Key": get_container().settings.api_key}


def make_release_dto() -> ReleaseDTO:
    file_mapping = ReleaseFileMappingDTO(
        mapping_type="movie",
        request_id="req-1",
        request_title="Req",
        season=None,
        episode=None,
    )
    file_dto = ReleaseFileDTO(
        id="file-1",
        name="File 1",
        size_bytes=1024,
        path="/path/file.mkv",
        request_mapping=file_mapping,
    )
    now = datetime.now(UTC)
    return ReleaseDTO(
        id="rel-1",
        name="Release 1",
        info_hash="HASH",
        size_bytes=2048,
        files=[file_dto],
        status=ReleaseStatus.PENDING,
        progress=0.0,
        download_speed=0.0,
        upload_speed=0.0,
        seeders=0,
        leechers=0,
        ratio=0.0,
        added_at=now,
        completed_at=None,
        request_ids=["req-1"],
        torrent_source="indexer",
        quality="1080p",
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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http_client:
        yield http_client


@pytest.mark.asyncio
async def test_list_releases_returns_results(client: AsyncClient) -> None:
    release = make_release_dto()
    page = ReleasesPageDTO(releases=[release], total=1, page=1, per_page=20)

    class FakeList:
        async def execute(self, options):  # type: ignore[override]
            return page

    with override_dependency(_list_use_case, FakeList()):
        response = await client.get("/releases", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["releases"][0]["id"] == release.id


@pytest.mark.asyncio
async def test_create_release_returns_created(client: AsyncClient) -> None:
    release = make_release_dto()

    class FakeCreate:
        async def execute(self, command):  # type: ignore[override]
            return release

    with override_dependency(_create_use_case, FakeCreate()):
        response = await client.post(
            "/releases",
            headers=API_KEY_HEADER,
            json={"magnet_link": "magnet:?xt=urn:btih:HASH", "request_ids": ["req-1"]},
        )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["id"] == release.id


@pytest.mark.asyncio
async def test_get_release_not_found_returns_404(client: AsyncClient) -> None:
    class FakeGet:
        async def execute(self, release_id):  # type: ignore[override]
            raise ReleaseNotFoundError(release_id)

    with override_dependency(_get_use_case, FakeGet()):
        response = await client.get("/releases/missing", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["code"] == "release_not_found"


@pytest.mark.asyncio
async def test_pause_release_sets_location_header(client: AsyncClient) -> None:
    op = AsyncOperationDTO(
        operation="pause_release",
        status="accepted",
        operation_id="op-1",
        location="/operations/op-1",
        message=None,
        resource_id="rel-1",
        details=None,
    )

    class FakePause:
        async def execute(self, release_id):  # type: ignore[override]
            return op

    with override_dependency(_pause_use_case, FakePause()):
        response = await client.post("/releases/rel-1/pause", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.headers.get("Location") == op.location


@pytest.mark.asyncio
async def test_update_file_mappings_returns_success(client: AsyncClient) -> None:
    class FakeUpdate:
        async def execute(self, command):  # type: ignore[override]
            return True

    with override_dependency(_update_mappings_use_case, FakeUpdate()):
        response = await client.put(
            "/releases/rel-1/files/mapping",
            headers=API_KEY_HEADER,
            json={"files": [{"file_id": "file-1", "request_mapping": None}]},
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_update_file_mappings_missing_file_returns_404(client: AsyncClient) -> None:
    class FakeUpdate:
        async def execute(self, command):  # type: ignore[override]
            raise ReleaseFileNotFoundError("rel-1", "file-1")

    with override_dependency(_update_mappings_use_case, FakeUpdate()):
        response = await client.put(
            "/releases/rel-1/files/mapping",
            headers=API_KEY_HEADER,
            json={"files": [{"file_id": "file-1", "request_mapping": None}]},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["code"] == "release_file_not_found"


@pytest.mark.asyncio
async def test_search_releases_returns_payload(client: AsyncClient) -> None:
    result = ReleaseSearchResultDTO(
        release_id="rel-1",
        release_name="Release 1",
        size="1 GB",
        magnet_link=None,
        torrent_file_url=None,
        info_url=None,
        seeders=10,
        leechers=1,
        quality="1080p",
        source="indexer",
        request_id="req-1",
    )
    response_dto = ReleaseSearchResponseDTO(results=[result], query="query", total_results=1)

    class FakeSearch:
        async def execute(self, command):  # type: ignore[override]
            return response_dto

    with override_dependency(_search_use_case, FakeSearch()):
        response = await client.get(
            "/releases/search", params={"q": "query"}, headers=API_KEY_HEADER
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["results"][0]["release_id"] == result.release_id


@pytest.mark.asyncio
async def test_queue_release_download_conflict_returns_409(client: AsyncClient) -> None:
    class FakeQueue:
        async def execute(self, command):  # type: ignore[override]
            raise ReleaseDownloadConflictError(command.request_id, command.release_id)

    with override_dependency(_queue_download_use_case, FakeQueue()):
        response = await client.post(
            "/requests/req-1/releases/download",
            headers=API_KEY_HEADER,
            json={"release_id": "rel-1"},
        )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["code"] == "release_download_conflict"


@pytest.mark.asyncio
async def test_missing_api_key_returns_401(client: AsyncClient) -> None:
    response = await client.get("/releases")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "code": "unauthorized",
        "message": "Invalid API key",
        "details": None,
    }
