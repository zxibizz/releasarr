"""Integration tests for the indexer API routes."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import status
from httpx import AsyncClient

from src.api.app import app
from src.api.routes.indexers import (
    _list_use_case,
    _run_all_tests_use_case,
    _run_test_use_case,
)
from src.application.interfaces.indexers import IndexerNotFoundError
from src.application.use_cases.indexers.dto import IndexerDTO, IndexerTestResultDTO
from src.application.use_cases.indexers.exceptions import ProwlarrNotConfiguredError
from src.core.container import get_container
from src.domain.enums import IndexerHealth
from src.infrastructure.http import HttpClientError

API_KEY_HEADER = {"X-API-Key": get_container().settings.api_key.get_secret_value()}


@contextmanager
def override_dependency(dep: Callable[..., Any], value: Any):
    app.dependency_overrides[dep] = lambda: value
    try:
        yield
    finally:
        app.dependency_overrides.pop(dep, None)


class FakeListUseCase:
    def __init__(
        self,
        indexers: list[IndexerDTO] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._indexers = indexers or []
        self._error = error

    async def execute(self) -> list[IndexerDTO]:
        if self._error is not None:
            raise self._error
        return self._indexers


class FakeTestUseCase:
    def __init__(
        self,
        result: IndexerTestResultDTO | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.calls: list[int] = []

    async def execute(self, indexer_id: int) -> IndexerTestResultDTO:
        self.calls.append(indexer_id)
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


class FakeTestAllUseCase:
    def __init__(
        self,
        results: list[IndexerTestResultDTO] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._results = results or []
        self._error = error

    async def execute(self) -> list[IndexerTestResultDTO]:
        if self._error is not None:
            raise self._error
        return self._results


def _indexer(**overrides: Any) -> IndexerDTO:
    defaults: dict[str, Any] = {
        "indexer_id": 2,
        "name": "Zeta Tracker",
        "health": IndexerHealth.BLOCKED,
        "enabled": True,
        "protocol": "torrent",
        "privacy": "private",
        "priority": 25,
        "supports_search": True,
        "supports_rss": True,
        "indexer_urls": ("https://zeta.example/",),
        "disabled_till": datetime(2026, 3, 4, 12, 30, tzinfo=UTC),
        "most_recent_failure": datetime(2026, 3, 4, 0, 30, tzinfo=UTC),
        "initial_failure": None,
    }
    return IndexerDTO(**(defaults | overrides))


@pytest.mark.asyncio
async def test_list_indexers_returns_the_payload(api_client: AsyncClient) -> None:
    with override_dependency(_list_use_case, FakeListUseCase([_indexer()])):
        response = await api_client.get("/indexers", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()["indexers"][0]
    assert payload["id"] == 2
    assert payload["name"] == "Zeta Tracker"
    assert payload["health"] == "blocked"
    assert payload["enabled"] is True
    assert payload["indexer_urls"] == ["https://zeta.example/"]
    assert payload["disabled_till"] == "2026-03-04T12:30:00Z"
    assert payload["initial_failure"] is None


@pytest.mark.asyncio
async def test_list_indexers_reports_missing_configuration_as_unavailable(
    api_client: AsyncClient,
) -> None:
    use_case = FakeListUseCase(error=ProwlarrNotConfiguredError())
    with override_dependency(_list_use_case, use_case):
        response = await api_client.get("/indexers", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["code"] == "prowlarr_not_configured"


@pytest.mark.asyncio
async def test_list_indexers_reports_an_unreachable_prowlarr_as_bad_gateway(
    api_client: AsyncClient,
) -> None:
    use_case = FakeListUseCase(error=HttpClientError("boom"))
    with override_dependency(_list_use_case, use_case):
        response = await api_client.get("/indexers", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert response.json()["code"] == "upstream_error"


@pytest.mark.asyncio
async def test_list_indexers_requires_the_api_key(api_client: AsyncClient) -> None:
    response = await api_client.get("/indexers")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_testing_one_indexer_returns_its_result(api_client: AsyncClient) -> None:
    result = IndexerTestResultDTO(
        indexer_id=2,
        success=False,
        name="Zeta Tracker",
        errors=("Request timed out",),
    )
    use_case = FakeTestUseCase(result)
    with override_dependency(_run_test_use_case, use_case):
        response = await api_client.post("/indexers/2/test", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_200_OK
    assert use_case.calls == [2]
    payload = response.json()
    assert payload == {
        "indexer_id": 2,
        "success": False,
        "name": "Zeta Tracker",
        "errors": ["Request timed out"],
    }


@pytest.mark.asyncio
async def test_testing_an_unknown_indexer_is_a_not_found(api_client: AsyncClient) -> None:
    use_case = FakeTestUseCase(error=IndexerNotFoundError("nope"))
    with override_dependency(_run_test_use_case, use_case):
        response = await api_client.post("/indexers/99/test", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["code"] == "indexer_not_found"


@pytest.mark.asyncio
async def test_testing_all_indexers_returns_every_result(api_client: AsyncClient) -> None:
    results = [
        IndexerTestResultDTO(indexer_id=1, success=True, name="Alpha"),
        IndexerTestResultDTO(indexer_id=2, success=False, name="Zeta", errors=("Nope",)),
    ]
    with override_dependency(_run_all_tests_use_case, FakeTestAllUseCase(results)):
        response = await api_client.post("/indexers/test", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()["results"]
    assert [(entry["indexer_id"], entry["success"]) for entry in payload] == [(1, True), (2, False)]
    assert payload[1]["errors"] == ["Nope"]


@pytest.mark.asyncio
async def test_testing_all_indexers_without_prowlarr_is_unavailable(
    api_client: AsyncClient,
) -> None:
    use_case = FakeTestAllUseCase(error=ProwlarrNotConfiguredError())
    with override_dependency(_run_all_tests_use_case, use_case):
        response = await api_client.post("/indexers/test", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["code"] == "prowlarr_not_configured"
