"""Integration tests for release API routes."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import status
from httpx import AsyncClient

from src.api.app import app
from src.api.routes.releases import (
    _create_use_case,
    _delete_use_case,
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
    ReleaseDownloadFailedError,
    ReleaseFileNotFoundError,
    ReleaseNotFoundError,
)
from src.core.container import get_container
from src.domain.enums import ReleaseStatus

API_KEY_HEADER = {"X-API-Key": get_container().settings.api_key.get_secret_value()}


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


@pytest.mark.asyncio
async def test_list_releases_returns_results(api_client: AsyncClient) -> None:
    release = make_release_dto()
    page = ReleasesPageDTO(releases=[release], total=1, page=1, per_page=20)

    class FakeList:
        async def execute(self, options):
            return page

    with override_dependency(_list_use_case, FakeList()):
        response = await api_client.get("/releases", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["releases"][0]["id"] == release.id


@pytest.mark.asyncio
async def test_list_releases_for_request_filters(api_client: AsyncClient) -> None:
    release = make_release_dto()
    page = ReleasesPageDTO(releases=[release], total=1, page=1, per_page=20)

    class FakeList:
        async def execute(self, options):
            assert options.request_id == "req-1"
            assert options.status == ReleaseStatus.PENDING
            return page

    with override_dependency(_list_use_case, FakeList()):
        response = await api_client.get(
            "/requests/req-1/releases",
            params={"status": ReleaseStatus.PENDING.value},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["releases"][0]["id"] == release.id


@pytest.mark.asyncio
async def test_list_releases_for_request_invalid_status(api_client: AsyncClient) -> None:
    class FakeList:
        async def execute(self, options):
            return ReleasesPageDTO(releases=[], total=0, page=1, per_page=20)

    with override_dependency(_list_use_case, FakeList()):
        response = await api_client.get(
            "/requests/req-1/releases",
            params={"status": "bad"},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["code"] == "invalid_status_filter"


@pytest.mark.asyncio
async def test_create_release_returns_created(api_client: AsyncClient) -> None:
    release = make_release_dto()

    class FakeCreate:
        async def execute(self, command):
            return release

    with override_dependency(_create_use_case, FakeCreate()):
        response = await api_client.post(
            "/releases",
            headers=API_KEY_HEADER,
            json={"magnet_link": "magnet:?xt=urn:btih:HASH", "request_ids": ["req-1"]},
        )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["id"] == release.id


@pytest.mark.asyncio
async def test_get_release_not_found_returns_404(api_client: AsyncClient) -> None:
    class FakeGet:
        async def execute(self, release_id):
            raise ReleaseNotFoundError(release_id)

    with override_dependency(_get_use_case, FakeGet()):
        response = await api_client.get("/releases/missing", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["code"] == "release_not_found"


@pytest.mark.asyncio
async def test_delete_release_returns_no_content(api_client: AsyncClient) -> None:
    class FakeDelete:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def execute(self, release_id):
            self.calls.append(release_id)

    fake_delete = FakeDelete()

    with override_dependency(_delete_use_case, fake_delete):
        response = await api_client.delete("/releases/rel-1", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert fake_delete.calls == ["rel-1"]
    assert response.content == b""


@pytest.mark.asyncio
async def test_delete_release_not_found_returns_404(api_client: AsyncClient) -> None:
    class FakeDelete:
        async def execute(self, release_id):
            raise ReleaseNotFoundError(release_id)

    with override_dependency(_delete_use_case, FakeDelete()):
        response = await api_client.delete("/releases/missing", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["code"] == "release_not_found"


@pytest.mark.asyncio
async def test_pause_release_sets_location_header(api_client: AsyncClient) -> None:
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
        async def execute(self, release_id):
            return op

    with override_dependency(_pause_use_case, FakePause()):
        response = await api_client.post("/releases/rel-1/pause", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.headers.get("Location") == op.location


@pytest.mark.asyncio
async def test_update_file_mappings_returns_success(api_client: AsyncClient) -> None:
    class FakeUpdate:
        async def execute(self, command):
            return True

    with override_dependency(_update_mappings_use_case, FakeUpdate()):
        response = await api_client.put(
            "/releases/rel-1/files/mapping",
            headers=API_KEY_HEADER,
            json={"files": [{"file_id": "file-1", "request_mapping": None}]},
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_update_file_mappings_missing_file_returns_404(api_client: AsyncClient) -> None:
    class FakeUpdate:
        async def execute(self, command):
            raise ReleaseFileNotFoundError("rel-1", "file-1")

    with override_dependency(_update_mappings_use_case, FakeUpdate()):
        response = await api_client.put(
            "/releases/rel-1/files/mapping",
            headers=API_KEY_HEADER,
            json={"files": [{"file_id": "file-1", "request_mapping": None}]},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["code"] == "release_file_not_found"


@pytest.mark.asyncio
async def test_search_releases_returns_payload(api_client: AsyncClient) -> None:
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
        async def execute(self, command):
            return response_dto

    with override_dependency(_search_use_case, FakeSearch()):
        response = await api_client.get(
            "/releases/search", params={"q": "query"}, headers=API_KEY_HEADER
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["results"][0]["release_id"] == result.release_id


@pytest.mark.asyncio
async def test_queue_release_download_conflict_returns_409(api_client: AsyncClient) -> None:
    class FakeQueue:
        async def execute(self, command):
            raise ReleaseDownloadConflictError(command.request_id, command.release_id)

    with override_dependency(_queue_download_use_case, FakeQueue()):
        response = await api_client.post(
            "/requests/req-1/releases/download",
            headers=API_KEY_HEADER,
            json={"release_id": "rel-1"},
        )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["code"] == "release_download_conflict"


@pytest.mark.asyncio
async def test_queue_release_download_failure_returns_500(api_client: AsyncClient) -> None:
    class FakeQueue:
        async def execute(self, command):
            raise ReleaseDownloadFailedError(command.release_id, "client offline")

    with override_dependency(_queue_download_use_case, FakeQueue()):
        response = await api_client.post(
            "/requests/req-1/releases/download",
            headers=API_KEY_HEADER,
            json={"release_id": "rel-1"},
        )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    payload = response.json()
    assert payload["code"] == "release_download_failed"
    assert "client offline" in payload["message"]


@pytest.mark.asyncio
async def test_missing_api_key_returns_401(api_client: AsyncClient) -> None:
    response = await api_client.get("/releases")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "code": "unauthorized",
        "message": "Invalid API key",
        "details": None,
    }
