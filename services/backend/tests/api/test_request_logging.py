"""Tests for the API's own access logging.

uvicorn's access log never reaches the file /logs reads, because uvicorn
configures its loggers with ``propagate: false``. The API logs its own requests
instead, and these tests pin that a request produces one usable record.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from httpx import AsyncClient
from loguru import logger

from src.api.app import app
from src.api.dependencies.auth import get_principal

API_KEY_HEADER: dict[str, str] = {}


@pytest.fixture()
def captured_records() -> Iterator[list[dict[str, Any]]]:
    """Like the shared fixture, but at DEBUG: the access log sits below the
    file sink's INFO floor, so the shared fixture would miss it entirely.
    """

    records: list[dict[str, Any]] = []
    sink_id = logger.add(
        lambda message: records.append(
            {
                "message": message.record["message"],
                "level": message.record["level"].name,
                **message.record["extra"],
            }
        ),
        level="DEBUG",
    )
    try:
        yield records
    finally:
        logger.remove(sink_id)


@pytest.mark.asyncio
async def test_a_served_request_is_logged(
    api_client: AsyncClient, captured_records: list[dict[str, Any]]
) -> None:
    response = await api_client.get("/healthz")

    assert response.status_code == 200
    entry = next(record for record in captured_records if record["message"] == "GET /healthz")
    assert entry["level"] == "DEBUG"
    assert entry["component"] == "api.http"
    assert entry["status_code"] == 200
    assert isinstance(entry["duration_ms"], int)


@pytest.mark.asyncio
async def test_an_auth_request_is_tagged_api_auth(
    api_client: AsyncClient, captured_records: list[dict[str, Any]]
) -> None:
    """Login and refresh lines are the bulk of the chatter, so they get their
    own component to filter on."""

    response = await api_client.post("/auth/logout")

    assert response.status_code == 204
    entry = next(record for record in captured_records if record["message"] == "POST /auth/logout")
    assert entry["level"] == "DEBUG"
    assert entry["component"] == "api.auth"


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

    messages = [
        record["message"] for record in captured_records if record.get("component") == "api.http"
    ]
    assert messages == ["GET /logs"]
