"""Interfaces for runtime-editable application settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from src.settings.config import AppSettings


@dataclass(slots=True)
class AppSettingsRecord:
    """The singleton settings override row."""

    id: str
    # Field key -> coerced value, only for keys the environment does not set.
    overrides: dict[str, Any]
    # Bumped on every write; the two processes watch it to know when to rebuild
    # their integration clients.
    revision: int


class AppSettingsRepository(Protocol):
    """Protocol describing persistence for the singleton settings override row."""

    async def get(self) -> AppSettingsRecord | None:
        """Fetch the override row, if one exists yet."""

    async def save_overrides(self, *, overrides: dict[str, Any]) -> AppSettingsRecord:
        """Store a new override map, bumping the revision. Creates the row if absent."""

    async def get_revision(self) -> int:
        """The current revision, or 0 when no row exists. Cheap, for staleness checks."""


class SettingsProvider(Protocol):
    """Resolves the effective settings: environment layer plus DB overrides.

    A field present in the environment layer (env var or ``.env``) is locked and
    always wins over a stored override, so a redeployed container keeps meaning
    what its ``.env`` says.
    """

    def current(self) -> AppSettings:
        """The effective settings right now."""

    def locked_keys(self) -> frozenset[str]:
        """Field keys the environment layer sets explicitly, which PATCH must refuse."""

    def current_revision(self) -> int:
        """The revision the currently-resolved settings were built from."""

    async def refresh_if_stale(self) -> bool:
        """Re-resolve when the stored revision moved. Returns True when it changed.

        Rate-limited internally to one revision read per interval, so it is safe
        to call on every request and every scheduler tick.
        """

    async def reload_now(self) -> None:
        """Force a re-resolve, used right after a write so the same request sees it."""


__all__ = [
    "AppSettingsRecord",
    "AppSettingsRepository",
    "SettingsProvider",
]
