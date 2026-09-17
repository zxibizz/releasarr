"""Runtime settings provider: environment layer plus stored overrides.

``AppContainer`` resolves its settings through this rather than calling
``get_settings()`` directly, so an override written through the API reaches both
the API process and the scheduler without a restart. The environment layer keeps
its ``lru_cache`` and stays authoritative for whatever it sets explicitly.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from src.application.interfaces.settings import AppSettingsRepository, SettingsProvider
from src.settings.config import AppSettings, get_settings
from src.settings.registry import FIELDS_BY_KEY, coerce_value

_REFRESH_INTERVAL_SECONDS = 10.0


@dataclass(slots=True)
class LayeredSettingsProvider(SettingsProvider):
    """Resolve effective settings by layering stored overrides onto the environment.

    A field the environment layer sets explicitly (it is in the env instance's
    ``model_fields_set``) is locked: the stored override for it is ignored, so a
    redeployed container keeps meaning what its ``.env`` says.
    """

    _repository: AppSettingsRepository
    # The env/.env layer. Defaults to the process-level ``get_settings()`` so the
    # API and scheduler get the same base; the container passes its own settings
    # when they were injected explicitly (as in tests).
    _env_base: AppSettings | None = None

    _env: AppSettings = field(init=False)
    _resolved: AppSettings = field(init=False)
    _revision: int = field(default=0, init=False)
    _overrides: dict[str, Any] = field(default_factory=dict, init=False)
    _last_check: float = field(default=0.0, init=False)
    _loaded: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        self._env = self._env_base if self._env_base is not None else get_settings()
        self._resolved = self._env

    def locked_keys(self) -> frozenset[str]:
        return frozenset(self._env.model_fields_set)

    def current(self) -> AppSettings:
        return self._resolved

    def current_revision(self) -> int:
        return self._revision

    async def refresh_if_stale(self) -> bool:
        """Re-resolve when the stored revision moved, at most once per interval."""

        now = time.monotonic()
        if not self._loaded:
            await self._reload()
            self._loaded = True
            self._last_check = now
            return True

        if now - self._last_check < _REFRESH_INTERVAL_SECONDS:
            return False

        self._last_check = now
        stored = await self._repository.get_revision()
        if stored == self._revision:
            return False

        await self._reload()
        return True

    async def reload_now(self) -> None:
        """Force a re-resolve, used right after a write so the same request sees it."""

        await self._reload()
        self._loaded = True
        self._last_check = time.monotonic()

    async def _reload(self) -> None:
        record = await self._repository.get()
        overrides = dict(record.overrides) if record is not None else {}
        self._revision = record.revision if record is not None else 0
        self._overrides = overrides
        self._resolved = self._apply(overrides)

    def _apply(self, overrides: dict[str, Any]) -> AppSettings:
        locked = self.locked_keys()
        update: dict[str, Any] = {}
        for key, value in overrides.items():
            if key in locked:
                continue
            field = FIELDS_BY_KEY.get(key)
            if field is None:
                continue
            update[key] = coerce_value(field, value)
        return self._env.model_copy(update=update) if update else self._env


__all__ = ["LayeredSettingsProvider"]
