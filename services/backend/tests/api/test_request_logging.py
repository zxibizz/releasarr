"""Tests for the API's own access logging.

uvicorn's access log never reaches the file /logs reads, because uvicorn
configures its loggers with ``propagate: false``. The API logs its own requests
instead, and these tests pin that a request produces one usable record.
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from src.api.app import app
from src.api.dependencies.auth import get_principal

API_KEY_HEADER: dict[str, str] = {}


@pytest.mark.asyncio
async def test_a_served_request_is_logged(
    api_client: AsyncClient, captured_records: list[dict[str, Any]]
) -> None:
    response = await api_client.get("/healthz")

    assert response.status_code == 200
    entry = next(record for record in captured_records if record["message"] == "GET /healthz")
    assert entry["level"] == "INFO"
    assert entry["status_code"] == 200
    assert isinstance(entry["duration_ms"], int)


@pytest.mark.asyncio
async def test_a_rejected_request_records_its_status(
    api_client: AsyncClient, captured_records: list[dict[str, Any]]
) -> None:
    """A request that never reaches a route is still worth a line."""

    app.dependency_overrides.pop(get_principal, None)
    response = await api_client.get("/logs")

    assert response.status_code == 401
    entry = next(record for record in captured_records if record["message"] == "GET /logs")
    assert entry["status_code"] == 401


@pytest.mark.asyncio
async def test_the_query_string_is_not_recorded(
    api_client: AsyncClient, captured_records: list[dict[str, Any]]
) -> None:
    """The log file is served to the browser, so a credential must not reach it."""

    await api_client.get("/logs", params={"api_key": "SUPERSECRET"}, headers=API_KEY_HEADER)

    assert [record["message"] for record in captured_records] == ["GET /logs"]
