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
from src.api.dependencies.auth import get_principal
from src.api.routes.indexers import (
    _history_use_case,
    _list_use_case,
    _logs_use_case,
    _run_all_tests_use_case,
    _run_test_use_case,
)
from src.application.interfaces.indexers import IndexerNotFoundError
from src.application.use_cases.indexers.dto import (
    IndexerDTO,
    IndexerEventDTO,
    IndexerHistoryPageDTO,
    IndexerLogDTO,
    IndexerLogsPageDTO,
    IndexerTestResultDTO,
)
from src.application.use_cases.indexers.exceptions import ProwlarrNotConfiguredError
from src.domain.enums import IndexerEventType, IndexerHealth, IndexerLogLevel
from src.infrastructure.http import HttpClientError

API_KEY_HEADER: dict[str, str] = {}


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


class FakeHistoryUseCase:
    def __init__(
        self,
        page: IndexerHistoryPageDTO | None = None,
        error: Exception | None = None,
    ) -> None:
        self._page = page or IndexerHistoryPageDTO(events=(), total=0, page=1, per_page=20)
        self._error = error
        self.calls: list[dict[str, Any]] = []

    async def execute(
        self,
        page: int | None = None,
        per_page: int | None = None,
        indexer_id: int | None = None,
        event_type: IndexerEventType | None = None,
    ) -> IndexerHistoryPageDTO:
        self.calls.append(
            {
                "page": page,
                "per_page": per_page,
                "indexer_id": indexer_id,
                "event_type": event_type,
            }
        )
        if self._error is not None:
            raise self._error
        return self._page


class FakeLogsUseCase:
    def __init__(
        self,
        page: IndexerLogsPageDTO | None = None,
        error: Exception | None = None,
    ) -> None:
        self._page = page or IndexerLogsPageDTO(logs=(), total=0, page=1, per_page=20)
        self._error = error
        self.calls: list[dict[str, Any]] = []

    async def execute(
        self,
        page: int | None = None,
        per_page: int | None = None,
        min_level: IndexerLogLevel | None = None,
    ) -> IndexerLogsPageDTO:
        self.calls.append({"page": page, "per_page": per_page, "min_level": min_level})
        if self._error is not None:
            raise self._error
        return self._page


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
    app.dependency_overrides.pop(get_principal, None)
    response = await api_client.get("/indexers")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_indexer_logs_returns_the_page(api_client: AsyncClient) -> None:
    entry = IndexerLogDTO(
        log_id=9000,
        occurred_at=datetime(2026, 3, 4, 11, 58, tzinfo=UTC),
        level=IndexerLogLevel.WARN,
        message="Request for RuTracker.org failed with status 525.",
        component="RuTracker",
        method="GET",
        exception="System.Net.Http.HttpRequestException: boom",
        exception_type="System.Net.Http.HttpRequestException",
    )
    page = IndexerLogsPageDTO(logs=(entry,), total=318, page=2, per_page=50)

    with override_dependency(_logs_use_case, FakeLogsUseCase(page)):
        response = await api_client.get("/indexers/logs", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert (body["total"], body["page"], body["per_page"]) == (318, 2, 50)
    assert body["logs"] == [
        {
            "id": 9000,
            "occurred_at": "2026-03-04T11:58:00Z",
            "level": "warn",
            "message": "Request for RuTracker.org failed with status 525.",
            "component": "RuTracker",
            "method": "GET",
            "exception": "System.Net.Http.HttpRequestException: boom",
            "exception_type": "System.Net.Http.HttpRequestException",
        }
    ]


@pytest.mark.asyncio
async def test_indexer_logs_forwards_the_level_threshold(api_client: AsyncClient) -> None:
    use_case = FakeLogsUseCase()
    with override_dependency(_logs_use_case, use_case):
        response = await api_client.get(
            "/indexers/logs",
            params={"page": 3, "per_page": 50, "min_level": "error"},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_200_OK
    assert use_case.calls == [{"page": 3, "per_page": 50, "min_level": IndexerLogLevel.ERROR}]


@pytest.mark.asyncio
async def test_indexer_logs_reject_a_level_it_does_not_define(api_client: AsyncClient) -> None:
    with override_dependency(_logs_use_case, FakeLogsUseCase()):
        response = await api_client.get(
            "/indexers/logs",
            params={"min_level": "Warn"},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
async def test_indexer_logs_without_prowlarr_is_unavailable(api_client: AsyncClient) -> None:
    use_case = FakeLogsUseCase(error=ProwlarrNotConfiguredError())
    with override_dependency(_logs_use_case, use_case):
        response = await api_client.get("/indexers/logs", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["code"] == "prowlarr_not_configured"


@pytest.mark.asyncio
async def test_indexer_logs_report_an_unreachable_prowlarr_as_bad_gateway(
    api_client: AsyncClient,
) -> None:
    use_case = FakeLogsUseCase(error=HttpClientError("boom"))
    with override_dependency(_logs_use_case, use_case):
        response = await api_client.get("/indexers/logs", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert response.json()["code"] == "upstream_error"


@pytest.mark.asyncio
async def test_indexer_history_returns_the_page(api_client: AsyncClient) -> None:
    event = IndexerEventDTO(
        event_id=412,
        indexer_id=2,
        occurred_at=datetime(2026, 3, 4, 11, 59, tzinfo=UTC),
        event_type=IndexerEventType.INDEXER_QUERY,
        successful=True,
        indexer_name="Zeta Tracker",
        query="Severance S02",
        title=None,
        source="Sonarr",
        elapsed_ms=412,
        data={"host": "sonarr.example"},
    )
    page = IndexerHistoryPageDTO(events=(event,), total=57, page=2, per_page=25)

    with override_dependency(_history_use_case, FakeHistoryUseCase(page)):
        response = await api_client.get("/indexers/history", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert (body["total"], body["page"], body["per_page"]) == (57, 2, 25)
    assert body["history"] == [
        {
            "id": 412,
            "indexer_id": 2,
            "occurred_at": "2026-03-04T11:59:00Z",
            "event_type": "indexer_query",
            "successful": True,
            "indexer_name": "Zeta Tracker",
            "query": "Severance S02",
            "title": None,
            "source": "Sonarr",
            "elapsed_ms": 412,
            "data": {"host": "sonarr.example"},
        }
    ]


@pytest.mark.asyncio
async def test_indexer_history_forwards_the_filters(api_client: AsyncClient) -> None:
    use_case = FakeHistoryUseCase()
    with override_dependency(_history_use_case, use_case):
        response = await api_client.get(
            "/indexers/history",
            params={"page": 3, "per_page": 50, "indexer_id": 2, "event_type": "release_grabbed"},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_200_OK
    assert use_case.calls == [
        {
            "page": 3,
            "per_page": 50,
            "indexer_id": 2,
            "event_type": IndexerEventType.RELEASE_GRABBED,
        }
    ]


@pytest.mark.asyncio
async def test_indexer_history_rejects_an_event_type_it_does_not_define(
    api_client: AsyncClient,
) -> None:
    with override_dependency(_history_use_case, FakeHistoryUseCase()):
        response = await api_client.get(
            "/indexers/history",
            params={"event_type": "indexerQuery"},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
async def test_indexer_history_without_prowlarr_is_unavailable(api_client: AsyncClient) -> None:
    use_case = FakeHistoryUseCase(error=ProwlarrNotConfiguredError())
    with override_dependency(_history_use_case, use_case):
        response = await api_client.get("/indexers/history", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["code"] == "prowlarr_not_configured"


@pytest.mark.asyncio
async def test_indexer_history_reports_an_unreachable_prowlarr_as_bad_gateway(
    api_client: AsyncClient,
) -> None:
    use_case = FakeHistoryUseCase(error=HttpClientError("boom"))
    with override_dependency(_history_use_case, use_case):
        response = await api_client.get("/indexers/history", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert response.json()["code"] == "upstream_error"


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
