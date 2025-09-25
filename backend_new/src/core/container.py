"""Application composition root.

The container keeps references to shared infrastructure (settings, db, clients).
Phase 0 stubs out the lifecycle hooks so later phases can populate them without
changing the FastAPI entrypoint signature.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from src.core.logging import configure_logging
from src.settings.config import AppSettings, get_settings


@dataclass(slots=True)
class AppContainer:
    settings: AppSettings

    def startup(self) -> None:
        """Hook for initializing resources (e.g. db engine, http clients)."""

        configure_logging(self.settings)
        return None

    def shutdown(self) -> None:
        """Hook for disposing resources during application shutdown."""

        # Intentionally left blank until infrastructure is implemented.
        return None

    def resolve(self, component: str) -> Any:
        """Generic lookup placeholder for future dependency resolution."""

        msg = f"Component '{component}' is not registered yet"
        raise LookupError(msg)


@lru_cache(maxsize=1)
def get_container() -> AppContainer:
    """Return the singleton application container."""

    settings = get_settings()
    return AppContainer(settings=settings)
