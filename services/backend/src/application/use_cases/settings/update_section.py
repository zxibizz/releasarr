"""Apply a partial update to one settings section."""

from __future__ import annotations

from typing import Any

from src.application.interfaces.settings import AppSettingsRepository, SettingsProvider
from src.application.use_cases.settings.exceptions import (
    EmptySettingsUpdateError,
    InvalidSettingValueError,
    SettingLockedError,
    UnknownSettingKeyError,
)
from src.settings.registry import FIELDS_BY_KEY, SettingsSection, coerce_value


class UpdateSettingsSectionUseCase:
    def __init__(self, repository: AppSettingsRepository, provider: SettingsProvider) -> None:
        self._repository = repository
        self._provider = provider

    async def execute(self, section: SettingsSection, values: dict[str, Any]) -> None:
        if not values:
            raise EmptySettingsUpdateError

        # Everything about the patch is validated before anything is written, so
        # a bad key or a locked field never leaves a half-applied section.
        locked = self._provider.locked_keys()

        coerced: dict[str, Any] = {}
        for key, value in values.items():
            field = FIELDS_BY_KEY.get(key)
            if field is None or field.section != section:
                raise UnknownSettingKeyError(key)
            if key in locked:
                raise SettingLockedError(key)
            try:
                coerced[key] = coerce_value(field, value)
            except ValueError as exc:
                raise InvalidSettingValueError(key, str(exc)) from exc

        # Merge into the stored overrides: fields not named keep their stored
        # value (or fall back to the environment), named ones take the new value.
        await self._provider.refresh_if_stale()
        record = await self._repository.get()
        merged: dict[str, Any] = dict(record.overrides) if record is not None else {}
        merged.update(coerced)

        await self._repository.save_overrides(overrides=merged)
        await self._provider.reload_now()


__all__ = ["UpdateSettingsSectionUseCase"]
