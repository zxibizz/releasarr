"""Read the effective runtime settings, resolved and sectioned for the API."""

from __future__ import annotations

from dataclasses import dataclass

from src.application.interfaces.settings import SettingsProvider
from src.settings.registry import READONLY_KEYS, SECTION_KEYS, SETTING_FIELDS


@dataclass(slots=True)
class SettingsView:
    """Effective values plus per-field behaviour, grouped by section."""

    values: dict[str, dict[str, object]]
    locked_keys: list[str]
    # Registry fields awaiting a restart, plus the always-readonly keys.
    restart_required_keys: list[str]


class GetSettingsUseCase:
    def __init__(self, provider: SettingsProvider) -> None:
        self._provider = provider

    async def execute(self) -> SettingsView:
        await self._provider.refresh_if_stale()
        settings = self._provider.current()
        locked = set(self._provider.locked_keys())

        values: dict[str, dict[str, object]] = {section: {} for section in SECTION_KEYS}
        for field in SETTING_FIELDS:
            value = getattr(settings, field.key)
            values[field.section][field.key] = value

        restart_required = [f.key for f in SETTING_FIELDS if f.requires_restart]
        restart_required.extend(READONLY_KEYS)

        return SettingsView(
            values=values,
            locked_keys=sorted(locked & _editable_keys()),
            restart_required_keys=restart_required,
        )


def _editable_keys() -> set[str]:
    return {f.key for f in SETTING_FIELDS}


__all__ = ["GetSettingsUseCase", "SettingsView"]
