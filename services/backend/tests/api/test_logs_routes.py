"""Integration tests for logs API routes."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

import pytest
from fastapi import status
from httpx import AsyncClient

from src.api.app import app
from src.api.dependencies.auth import get_principal
from src.api.routes.logs import _get_use_case
from src.application.queries.logs import LogsPageResult
from src.application.use_cases.logs.list_logs import ListLogsUseCase

API_KEY_HEADER: dict[str, str] = {}


class FakeLogsUseCase(ListLogsUseCase):
    def __init__(self, result: LogsPageResult) -> None:
        self._result = result
        self.calls: list[dict[str, Any]] = []

    async def execute(
        self,
        page: int,
        per_page: int,
        request_id: str | None = None,
        task: str | None = None,
        service: str | None = None,
        min_level: str | None = None,
    ) -> LogsPageResult:
        self.calls.append(
            {
                "page": page,
                "per_page": per_page,
                "request_id": request_id,
                "task": task,
                "service": service,
                "min_level": min_level,
            }
        )
        return self._result


def make_logs_result() -> LogsPageResult:
    return LogsPageResult(
        logs=[],
        total=0,
        page=1,
        per_page=20,
    )


@contextmanager
def override_dependency(dep: Callable[..., Any], value: Any):
    app.dependency_overrides[dep] = lambda: value
    try:
        yield
    finally:
        app.dependency_overrides.pop(dep, None)


@pytest.mark.asyncio
async def test_list_logs_returns_response(api_client: AsyncClient) -> None:
    result = make_logs_result()
    with override_dependency(_get_use_case, FakeLogsUseCase(result)):
        response = await api_client.get("/logs", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_logs_passes_the_task_filter_through(api_client: AsyncClient) -> None:
    use_case = FakeLogsUseCase(make_logs_result())

    with override_dependency(_get_use_case, use_case):
        response = await api_client.get(
            "/logs",
            params={"task": "release_sync"},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_200_OK
    assert use_case.calls[0]["task"] == "release_sync"


@pytest.mark.asyncio
async def test_list_logs_rejects_an_unknown_task(api_client: AsyncClient) -> None:
    use_case = FakeLogsUseCase(make_logs_result())

    with override_dependency(_get_use_case, use_case):
        response = await api_client.get(
            "/logs",
            params={"task": "not_a_task"},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert use_case.calls == []


@pytest.mark.asyncio
async def test_list_logs_without_filters_asks_for_everything(api_client: AsyncClient) -> None:
    use_case = FakeLogsUseCase(make_logs_result())

    with override_dependency(_get_use_case, use_case):
        await api_client.get("/logs", headers=API_KEY_HEADER)

    assert use_case.calls[0]["task"] is None
    assert use_case.calls[0]["request_id"] is None
    assert use_case.calls[0]["service"] is None


@pytest.mark.asyncio
async def test_list_logs_passes_the_service_filter_through(api_client: AsyncClient) -> None:
    use_case = FakeLogsUseCase(make_logs_result())

    with override_dependency(_get_use_case, use_case):
        response = await api_client.get(
            "/logs",
            params={"service": "scheduler"},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_200_OK
    assert use_case.calls[0]["service"] == "scheduler"


@pytest.mark.asyncio
async def test_list_logs_rejects_an_unknown_service(api_client: AsyncClient) -> None:
    use_case = FakeLogsUseCase(make_logs_result())

    with override_dependency(_get_use_case, use_case):
        response = await api_client.get(
            "/logs",
            params={"service": "not_a_process"},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert use_case.calls == []


@pytest.mark.asyncio
async def test_list_logs_passes_the_level_floor_through(api_client: AsyncClient) -> None:
    use_case = FakeLogsUseCase(make_logs_result())

    with override_dependency(_get_use_case, use_case):
        response = await api_client.get(
            "/logs",
            params={"min_level": "warning"},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_200_OK
    assert use_case.calls[0]["min_level"] == "warning"
    assert use_case.calls[0]["service"] is None


@pytest.mark.asyncio
async def test_list_logs_rejects_an_unknown_level(api_client: AsyncClient) -> None:
    use_case = FakeLogsUseCase(make_logs_result())

    with override_dependency(_get_use_case, use_case):
        response = await api_client.get(
            "/logs",
            params={"min_level": "shouty"},
            headers=API_KEY_HEADER,
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert use_case.calls == []


@pytest.mark.asyncio
async def test_missing_api_key_returns_401(api_client: AsyncClient) -> None:
    app.dependency_overrides.pop(get_principal, None)
    response = await api_client.get("/logs")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "code": "unauthorized",
        "message": "Authentication required",
        "details": None,
    }
