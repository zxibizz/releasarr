"""Shared pytest fixtures for backend tests."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import app


@pytest.fixture()
async def api_client() -> AsyncIterator[AsyncClient]:
    """Async HTTP client bound to the FastAPI app."""

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
