"""Integration tests for the system info route."""

from __future__ import annotations

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from src import __version__
from src.api.app import app
from src.api.dependencies.auth import get_principal
from src.api.routes.system import _get_use_case
from src.application.use_cases.system import GetSystemInfoUseCase


@pytest.mark.asyncio
async def test_system_status_reports_version_and_database(api_client: AsyncClient) -> None:
    app.dependency_overrides[_get_use_case] = lambda: GetSystemInfoUseCase(
        version="1.2.3", database="postgresql", url_base="/releasarr"
    )
    try:
        response = await api_client.get("/system/status")
    finally:
        app.dependency_overrides.pop(_get_use_case, None)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "app_name": "Releasarr",
        "version": "1.2.3",
        "database": "postgresql",
        "url_base": "/releasarr",
    }


@pytest.mark.asyncio
async def test_system_status_defaults_to_the_package_version(api_client: AsyncClient) -> None:
    response = await api_client.get("/system/status")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["version"] == __version__


@pytest.mark.asyncio
async def test_system_status_requires_authentication(api_client: AsyncClient) -> None:
    app.dependency_overrides.pop(get_principal, None)

    response = await api_client.get("/system/status")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_ping_answers_outside_the_api_prefix_without_authentication() -> None:
    app.dependency_overrides.pop(get_principal, None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/ping")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "OK"}
