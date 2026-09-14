"""Integration tests for the singleton service-key API routes."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import status
from httpx import AsyncClient

from src.api.app import app
from src.api.routes.service_keys import _get_use_case, _regenerate_use_case
from src.application.interfaces.auth import ServiceApiKeyRecord

API_KEY_HEADER: dict[str, str] = {}


@contextmanager
def override_dependency(dep: Callable[..., Any], value: Any):
    app.dependency_overrides[dep] = lambda: value
    try:
        yield
    finally:
        app.dependency_overrides.pop(dep, None)


class FakeGetOrCreate:
    def __init__(self, record: ServiceApiKeyRecord) -> None:
        self._record = record

    async def execute(self) -> ServiceApiKeyRecord:
        return self._record


class FakeRegenerate:
    def __init__(self, record: ServiceApiKeyRecord) -> None:
        self._record = record

    async def execute(self) -> ServiceApiKeyRecord:
        return self._record


def _make_record(**overrides: Any) -> ServiceApiKeyRecord:
    defaults: dict[str, Any] = {
        "id": "key-1",
        "key": "rlsr_abcdef1234567890",
        "last_used_at": None,
        "created_at": datetime(2026, 9, 14, 10, 0, tzinfo=UTC),
    }
    defaults.update(overrides)
    return ServiceApiKeyRecord(**defaults)


@pytest.mark.asyncio
async def test_get_service_key_returns_the_key(api_client: AsyncClient) -> None:
    record = _make_record()

    with override_dependency(_get_use_case, FakeGetOrCreate(record)):
        response = await api_client.get("/service-key", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body == {
        "key": "rlsr_abcdef1234567890",
        "last_used_at": None,
        "created_at": "2026-09-14T10:00:00Z",
    }


@pytest.mark.asyncio
async def test_regenerate_service_key_returns_the_new_key(api_client: AsyncClient) -> None:
    record = _make_record(id="key-2", key="rlsr_supersecret")

    with override_dependency(_regenerate_use_case, FakeRegenerate(record)):
        response = await api_client.post("/service-key/regenerate", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["key"] == "rlsr_supersecret"
