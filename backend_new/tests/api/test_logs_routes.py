"""Integration tests for logs API routes."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

import pytest
from fastapi import status
from httpx import AsyncClient

from src.api.app import app
from src.api.routes.logs import _get_use_case
from src.application.use_cases.logs.list_logs import ListLogsUseCase
from src.core.container import get_container
from src.schemas.logs import LogsResponse

API_KEY_HEADER = {"X-API-Key": get_container().settings.api_key}


class FakeLogsUseCase(ListLogsUseCase):  # type: ignore[misc]
    def __init__(self, response: LogsResponse) -> None:
        self._response = response

    async def execute(
        self, page: int, per_page: int, request_id: str | None = None
    ) -> LogsResponse:  # type: ignore[override]
        return self._response


def make_logs_response() -> LogsResponse:
    return LogsResponse(
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
    response_model = make_logs_response()
    with override_dependency(_get_use_case, FakeLogsUseCase(response_model)):
        response = await api_client.get("/logs", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["total"] == 0


@pytest.mark.asyncio
async def test_missing_api_key_returns_401(api_client: AsyncClient) -> None:
    response = await api_client.get("/logs")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "code": "unauthorized",
        "message": "Invalid API key",
        "details": None,
    }
