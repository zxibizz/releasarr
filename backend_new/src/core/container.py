"""Application composition root.

The container keeps references to shared infrastructure (settings, db, clients).
Phase 0 stubs out the lifecycle hooks so later phases can populate them without
changing the FastAPI entrypoint signature.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property, lru_cache

from src.application.queries.logs import ListLogsQuery
from src.application.queries.releases import ReleaseSummaryQuery
from src.application.use_cases.logs.list_logs import ListLogsUseCase
from src.core.logging import configure_logging
from src.db.session import DBManager, get_db_manager
from src.infrastructure.logs import LogFileReader
from src.infrastructure.media_requests import SqlAlchemyMediaRequestRepository
from src.infrastructure.releases import (
    InMemoryReleaseDownloadService,
    InMemoryReleaseLifecycleService,
    InMemoryReleaseSearchService,
    SqlAlchemyReleaseRepository,
)
from src.settings.config import AppSettings, get_settings


@dataclass
class RepositoryContainer:
    _container: AppContainer

    @cached_property
    def media_requests(self) -> SqlAlchemyMediaRequestRepository:
        return SqlAlchemyMediaRequestRepository(db=self._container.db_manager)

    @cached_property
    def releases(self) -> SqlAlchemyReleaseRepository:
        return SqlAlchemyReleaseRepository(db=self._container.db_manager)


@dataclass
class ServiceContainer:
    _container: AppContainer

    @cached_property
    def release_lifecycle(self) -> InMemoryReleaseLifecycleService:
        return InMemoryReleaseLifecycleService()

    @cached_property
    def release_search(self) -> InMemoryReleaseSearchService:
        return InMemoryReleaseSearchService()

    @cached_property
    def release_download(self) -> InMemoryReleaseDownloadService:
        return InMemoryReleaseDownloadService()


@dataclass
class QueryContainer:
    _container: AppContainer

    @cached_property
    def logs(self) -> ListLogsQuery:
        return ListLogsQuery(
            reader=self._container.infrastructure.log_reader, settings=self._container.settings
        )

    @cached_property
    def release_summary(self) -> ReleaseSummaryQuery:
        return ReleaseSummaryQuery(db=self._container.db_manager)


@dataclass
class UseCaseContainer:
    _container: AppContainer

    @cached_property
    def list_logs(self) -> ListLogsUseCase:
        return ListLogsUseCase(query=self._container.queries.logs)


@dataclass
class InfrastructureContainer:
    _container: AppContainer

    @cached_property
    def log_reader(self) -> LogFileReader:
        return LogFileReader(self._container.settings.log_file)


@dataclass
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

    @cached_property
    def db_manager(self) -> DBManager:
        return get_db_manager()

    @cached_property
    def repositories(self) -> RepositoryContainer:
        return RepositoryContainer(self)

    @cached_property
    def services(self) -> ServiceContainer:
        return ServiceContainer(self)

    @cached_property
    def queries(self) -> QueryContainer:
        return QueryContainer(self)

    @cached_property
    def use_cases(self) -> UseCaseContainer:
        return UseCaseContainer(self)

    @cached_property
    def infrastructure(self) -> InfrastructureContainer:
        return InfrastructureContainer(self)


@lru_cache(maxsize=1)
def get_container() -> AppContainer:
    """Return the singleton application container."""

    settings = get_settings()
    return AppContainer(settings=settings)
