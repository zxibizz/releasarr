"""Application composition root.

The container keeps references to shared infrastructure (settings, db, clients).
Phase 0 stubs out the lifecycle hooks so later phases can populate them without
changing the FastAPI entrypoint signature.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Callable

from src.core.logging import configure_logging
from src.db.session import get_db_manager
from src.infrastructure.media_requests import SqlAlchemyMediaRequestRepository
from src.infrastructure.releases import (
    InMemoryReleaseDownloadService,
    InMemoryReleaseLifecycleService,
    InMemoryReleaseSearchService,
    SqlAlchemyReleaseRepository,
)
from src.settings.config import AppSettings, get_settings


@dataclass(slots=True)
class AppContainer:
    settings: AppSettings
    _providers: dict[str, Callable[[], Any]] = field(default_factory=dict, init=False)
    _singletons: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._providers = {}
        self._singletons = {}
        self._register_defaults()

    def startup(self) -> None:
        """Hook for initializing resources (e.g. db engine, http clients)."""

        configure_logging(self.settings)
        return None

    def shutdown(self) -> None:
        """Hook for disposing resources during application shutdown."""

        # Intentionally left blank until infrastructure is implemented.
        return None

    def resolve(self, component: str) -> Any:
        """Retrieve a singleton dependency by name."""

        if component in self._singletons:
            return self._singletons[component]

        factory = self._providers.get(component)
        if factory is None:
            msg = f"Component '{component}' is not registered"
            raise LookupError(msg)

        instance = factory()
        self._singletons[component] = instance
        return instance

    def register_singleton(self, component: str, factory: Callable[[], Any]) -> None:
        """Register a lazily evaluated singleton factory."""

        self._providers[component] = factory

    def _register_defaults(self) -> None:
        """Populate default infrastructure bindings."""

        self.register_singleton("settings", lambda: self.settings)
        self.register_singleton("db_manager", get_db_manager)
        self.register_singleton(
            "media_request_repository",
            lambda: SqlAlchemyMediaRequestRepository(
                db=self.resolve("db_manager"),
            ),
        )
        self.register_singleton(
            "release_repository",
            lambda: SqlAlchemyReleaseRepository(
                db=self.resolve("db_manager"),
            ),
        )
        self.register_singleton(
            "release_lifecycle_service",
            InMemoryReleaseLifecycleService,
        )
        self.register_singleton(
            "release_search_service",
            InMemoryReleaseSearchService,
        )
        self.register_singleton(
            "release_download_service",
            InMemoryReleaseDownloadService,
        )


@lru_cache(maxsize=1)
def get_container() -> AppContainer:
    """Return the singleton application container."""

    settings = get_settings()
    return AppContainer(settings=settings)
