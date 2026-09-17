"""Tests for the runtime settings use cases and the layered provider."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from src.application.interfaces.settings import AppSettingsRecord
from src.application.use_cases.settings import (
    EmptySettingsUpdateError,
    GetSettingsUseCase,
    InvalidSettingValueError,
    SettingLockedError,
    UnknownSettingKeyError,
    UpdateSettingsSectionUseCase,
)
from src.infrastructure.settings import LayeredSettingsProvider
from src.settings.config import AppSettings


class InMemoryAppSettingsRepository:
    def __init__(self) -> None:
        self._overrides: dict = {}
        self._revision = 0

    async def get(self) -> AppSettingsRecord | None:
        if self._revision == 0:
            return None
        return AppSettingsRecord(
            id="app_settings", overrides=dict(self._overrides), revision=self._revision
        )

    async def save_overrides(self, *, overrides: dict) -> AppSettingsRecord:
        self._overrides = dict(overrides)
        self._revision += 1
        return AppSettingsRecord(
            id="app_settings", overrides=dict(self._overrides), revision=self._revision
        )

    async def get_revision(self) -> int:
        return self._revision

    async def delete(self) -> None:
        self._overrides = {}
        self._revision = 0


def _env(**overrides: object) -> AppSettings:
    return AppSettings(**overrides)


async def test_effective_settings_default_to_the_environment() -> None:
    env = _env(prowlarr_search_concurrency=9)
    provider = LayeredSettingsProvider(InMemoryAppSettingsRepository(), env)

    await provider.refresh_if_stale()

    assert provider.current().prowlarr_search_concurrency == 9


async def test_a_stored_override_layers_onto_the_environment() -> None:
    repo = InMemoryAppSettingsRepository()
    await repo.save_overrides(overrides={"prowlarr_search_concurrency": 12})
    provider = LayeredSettingsProvider(repo, _env())

    await provider.refresh_if_stale()

    assert provider.current().prowlarr_search_concurrency == 12


async def test_an_environment_pinned_field_is_locked_and_ignores_the_override() -> None:
    env = _env(sonarr_api_key=SecretStr("from-env"))
    repo = InMemoryAppSettingsRepository()
    await repo.save_overrides(overrides={"sonarr_api_key": "from-db"})
    provider = LayeredSettingsProvider(repo, env)

    await provider.refresh_if_stale()

    assert provider.current().sonarr_api_key.get_secret_value() == "from-env"
    assert "sonarr_api_key" in provider.locked_keys()


async def test_update_rejects_a_field_outside_its_section() -> None:
    _, use_case = _update(_env())

    with pytest.raises(UnknownSettingKeyError):
        await use_case.execute("network", {"prowlarr_url": "http://x"})


async def test_update_rejects_an_unknown_key() -> None:
    _, use_case = _update(_env())

    with pytest.raises(UnknownSettingKeyError):
        await use_case.execute("network", {"not_a_setting": 1})


async def test_update_rejects_an_empty_patch() -> None:
    _, use_case = _update(_env())

    with pytest.raises(EmptySettingsUpdateError):
        await use_case.execute("network", {})


async def test_update_rejects_a_locked_field() -> None:
    env = _env(prowlarr_search_concurrency=5)
    _, use_case = _update(env)

    with pytest.raises(SettingLockedError):
        await use_case.execute("network", {"prowlarr_search_concurrency": 7})


async def test_update_rejects_a_wrong_typed_value() -> None:
    _, use_case = _update(_env())

    with pytest.raises(InvalidSettingValueError):
        await use_case.execute("network", {"prowlarr_search_concurrency": "many"})


async def test_update_rejects_a_choice_outside_the_allowed_set() -> None:
    _, use_case = _update(_env())

    with pytest.raises(InvalidSettingValueError):
        await use_case.execute("logging", {"log_level": "VERBOSE"})


async def test_update_coerces_and_persists_a_valid_value() -> None:
    repo = InMemoryAppSettingsRepository()
    provider = LayeredSettingsProvider(repo, _env())
    use_case = UpdateSettingsSectionUseCase(repository=repo, provider=provider)

    await use_case.execute("network", {"prowlarr_search_concurrency": 11})

    assert (await repo.get()).overrides == {"prowlarr_search_concurrency": 11}
    assert provider.current().prowlarr_search_concurrency == 11


async def test_update_merges_with_existing_overrides() -> None:
    repo = InMemoryAppSettingsRepository()
    await repo.save_overrides(overrides={"log_json": True})
    provider = LayeredSettingsProvider(repo, _env())
    use_case = UpdateSettingsSectionUseCase(repository=repo, provider=provider)

    await use_case.execute("network", {"prowlarr_search_concurrency": 3})

    overrides = (await repo.get()).overrides
    assert overrides == {"log_json": True, "prowlarr_search_concurrency": 3}


async def test_update_bumps_the_revision() -> None:
    repo = InMemoryAppSettingsRepository()
    provider = LayeredSettingsProvider(repo, _env())
    use_case = UpdateSettingsSectionUseCase(repository=repo, provider=provider)

    await use_case.execute("network", {"prowlarr_search_concurrency": 3})
    await use_case.execute("logging", {"log_level": "DEBUG"})

    assert await repo.get_revision() == 2
    assert provider.current_revision() == 2


async def test_refresh_detects_an_external_write_via_the_revision() -> None:
    repo = InMemoryAppSettingsRepository()
    provider = LayeredSettingsProvider(repo, _env())
    await provider.refresh_if_stale()

    await repo.save_overrides(overrides={"prowlarr_search_concurrency": 21})
    provider._last_check = 0  # defeat the rate limiter for the test

    changed = await provider.refresh_if_stale()

    assert changed is True
    assert provider.current().prowlarr_search_concurrency == 21


async def test_get_settings_groups_values_by_section() -> None:
    provider = LayeredSettingsProvider(InMemoryAppSettingsRepository(), _env())
    use_case = GetSettingsUseCase(provider)

    view = await use_case.execute()

    assert "prowlarr_search_concurrency" in view.values["network"]
    assert "sonarr_url" in view.values["services"]
    assert "log_level" in view.values["logging"]
    assert view.locked_keys == []


async def test_get_settings_reports_locked_and_restart_required() -> None:
    env = _env(prowlarr_search_concurrency=5)
    provider = LayeredSettingsProvider(InMemoryAppSettingsRepository(), env)
    use_case = GetSettingsUseCase(provider)

    view = await use_case.execute()

    assert "prowlarr_search_concurrency" in view.locked_keys
    assert "auth_access_token_ttl_seconds" in view.restart_required_keys


def _update(env: AppSettings) -> tuple[LayeredSettingsProvider, UpdateSettingsSectionUseCase]:
    repo = InMemoryAppSettingsRepository()
    provider = LayeredSettingsProvider(repo, env)
    return provider, UpdateSettingsSectionUseCase(repository=repo, provider=provider)
