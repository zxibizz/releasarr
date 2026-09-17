"""Integration tests for the runtime settings API routes."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

import pytest
from fastapi import status
from httpx import AsyncClient

from src.api.app import app
from src.api.routes.settings import (
    _download_categories_use_case,
    _get_use_case,
    _indexer_categories_use_case,
    _quality_profiles_use_case,
    _test_use_case,
    _update_use_case,
)
from src.application.use_cases.indexers.exceptions import ProwlarrNotConfiguredError
from src.application.use_cases.releases.exceptions import QbittorrentNotConfiguredError
from src.application.use_cases.settings import (
    ConnectionTestResultDTO,
    IndexerCategoryOptionDTO,
    InvalidSettingValueError,
    QualityProfileOptionDTO,
    SettingLockedError,
    SettingsView,
    UnknownSettingKeyError,
)

API_KEY_HEADER: dict[str, str] = {}


@contextmanager
def override_dependency(dep: Callable[..., Any], value: Any):
    app.dependency_overrides[dep] = lambda: value
    try:
        yield
    finally:
        app.dependency_overrides.pop(dep, None)


def _view(values: dict[str, dict[str, Any]] | None = None) -> SettingsView:
    return SettingsView(
        values=values or {"network": {"prowlarr_search_concurrency": 5}},
        locked_keys=[],
        restart_required_keys=[],
    )


class FakeGet:
    def __init__(self, view: SettingsView) -> None:
        self._view = view

    async def execute(self) -> SettingsView:
        return self._view


class FakeUpdate:
    def __init__(self, error: Exception | None = None) -> None:
        self._error = error
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def execute(self, section: str, values: dict[str, Any]) -> None:
        self.calls.append((section, values))
        if self._error is not None:
            raise self._error


class FakeTest:
    def __init__(self, success: bool) -> None:
        self._success = success

    async def execute(self, integration: str, command: Any) -> ConnectionTestResultDTO:
        return ConnectionTestResultDTO(
            integration=integration,
            success=self._success,
            detail=None if self._success else "boom",
        )


@pytest.mark.asyncio
async def test_get_settings_returns_the_sectioned_view(api_client: AsyncClient) -> None:
    with override_dependency(_get_use_case, FakeGet(_view())):
        response = await api_client.get("/settings", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["values"]["network"]["prowlarr_search_concurrency"] == 5
    assert "fields" in body
    assert body["locked_keys"] == []


@pytest.mark.asyncio
async def test_patch_forwards_the_section_and_values(api_client: AsyncClient) -> None:
    update = FakeUpdate()
    with (
        override_dependency(_update_use_case, update),
        override_dependency(_get_use_case, FakeGet(_view())),
    ):
        response = await api_client.patch(
            "/settings/network",
            headers=API_KEY_HEADER,
            json={"values": {"prowlarr_search_concurrency": 11}},
        )

    assert response.status_code == status.HTTP_200_OK
    assert update.calls == [("network", {"prowlarr_search_concurrency": 11})]


@pytest.mark.asyncio
async def test_patch_rejects_an_unknown_key(api_client: AsyncClient) -> None:
    with (
        override_dependency(_update_use_case, FakeUpdate(UnknownSettingKeyError("nope"))),
        override_dependency(_get_use_case, FakeGet(_view())),
    ):
        response = await api_client.patch(
            "/settings/network", headers=API_KEY_HEADER, json={"values": {"nope": 1}}
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "unknown_setting"


@pytest.mark.asyncio
async def test_patch_rejects_a_locked_field(api_client: AsyncClient) -> None:
    with (
        override_dependency(_update_use_case, FakeUpdate(SettingLockedError("log_level"))),
        override_dependency(_get_use_case, FakeGet(_view())),
    ):
        response = await api_client.patch(
            "/settings/logging", headers=API_KEY_HEADER, json={"values": {"log_level": "DEBUG"}}
        )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["code"] == "setting_locked"


@pytest.mark.asyncio
async def test_patch_rejects_an_invalid_value(api_client: AsyncClient) -> None:
    with (
        override_dependency(
            _update_use_case,
            FakeUpdate(
                InvalidSettingValueError("prowlarr_search_concurrency", "must be an integer")
            ),
        ),
        override_dependency(_get_use_case, FakeGet(_view())),
    ):
        response = await api_client.patch(
            "/settings/network",
            headers=API_KEY_HEADER,
            json={"values": {"prowlarr_search_concurrency": "many"}},
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["code"] == "invalid_setting_value"


@pytest.mark.asyncio
async def test_connection_test_reports_failure(api_client: AsyncClient) -> None:
    with override_dependency(_test_use_case, FakeTest(success=False)):
        response = await api_client.post("/settings/test/sonarr", headers=API_KEY_HEADER)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"integration": "sonarr", "success": False, "detail": "boom"}


@pytest.mark.asyncio
async def test_connection_test_reports_success(api_client: AsyncClient) -> None:
    with override_dependency(_test_use_case, FakeTest(success=True)):
        response = await api_client.post(
            "/settings/test/qbittorrent",
            headers=API_KEY_HEADER,
            json={"url": "http://qb:8080/api/v2", "username": "admin", "password": "x"},
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"integration": "qbittorrent", "success": True, "detail": None}


class FakeOptions:
    def __init__(self, result: Any = None, error: Exception | None = None) -> None:
        self._result = result
        self._error = error
        self.calls: list[Any] = []

    async def execute(self, *args: Any) -> Any:
        self.calls.append(args)
        if self._error is not None:
            raise self._error
        return self._result


@pytest.mark.asyncio
async def test_quality_profile_options_name_each_profile(api_client: AsyncClient) -> None:
    use_case = FakeOptions(
        [QualityProfileOptionDTO(profile_id=4, name="HD-1080p")],
    )
    with override_dependency(_quality_profiles_use_case, use_case):
        response = await api_client.get(
            "/settings/options/quality-profiles/sonarr", headers=API_KEY_HEADER
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"profiles": [{"id": 4, "name": "HD-1080p"}]}
    assert use_case.calls == [("sonarr",)]


@pytest.mark.asyncio
async def test_quality_profile_options_reject_a_service_without_profiles(
    api_client: AsyncClient,
) -> None:
    response = await api_client.get(
        "/settings/options/quality-profiles/prowlarr", headers=API_KEY_HEADER
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
async def test_indexer_category_options_merge_into_one_list(api_client: AsyncClient) -> None:
    use_case = FakeOptions([IndexerCategoryOptionDTO(category_id=5000, name="TV")])
    with override_dependency(_indexer_categories_use_case, use_case):
        response = await api_client.get(
            "/settings/options/indexer-categories", headers=API_KEY_HEADER
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"categories": [{"id": 5000, "name": "TV"}]}


@pytest.mark.asyncio
async def test_indexer_category_options_say_prowlarr_is_absent(api_client: AsyncClient) -> None:
    with override_dependency(
        _indexer_categories_use_case, FakeOptions(error=ProwlarrNotConfiguredError())
    ):
        response = await api_client.get(
            "/settings/options/indexer-categories", headers=API_KEY_HEADER
        )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["code"] == "prowlarr_not_configured"


@pytest.mark.asyncio
async def test_download_category_options_list_the_client_names(api_client: AsyncClient) -> None:
    with override_dependency(_download_categories_use_case, FakeOptions(["releasarr", "tv"])):
        response = await api_client.get(
            "/settings/options/download-categories", headers=API_KEY_HEADER
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"categories": ["releasarr", "tv"]}


@pytest.mark.asyncio
async def test_download_category_options_say_qbittorrent_is_absent(
    api_client: AsyncClient,
) -> None:
    with override_dependency(
        _download_categories_use_case, FakeOptions(error=QbittorrentNotConfiguredError())
    ):
        response = await api_client.get(
            "/settings/options/download-categories", headers=API_KEY_HEADER
        )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
