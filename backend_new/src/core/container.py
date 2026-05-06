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
from src.infrastructure.media_requests import SqlAlchemyMediaRequestRepository
from src.infrastructure.releases import (
    InMemoryReleaseDownloadService,
    InMemoryReleaseLifecycleService,
    InMemoryReleaseSearchService,
    SqlAlchemyReleaseRepository,
)
from src.infrastructure.logs import LogFileReader
from src.settings.config import AppSettings, get_settings


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
    def media_request_repository(self) -> SqlAlchemyMediaRequestRepository:
        return SqlAlchemyMediaRequestRepository(db=self.db_manager)

    @cached_property
    def release_repository(self) -> SqlAlchemyReleaseRepository:
        return SqlAlchemyReleaseRepository(db=self.db_manager)

    @cached_property
    def release_lifecycle_service(self) -> InMemoryReleaseLifecycleService:
        return InMemoryReleaseLifecycleService()

    @cached_property
    def release_search_service(self) -> InMemoryReleaseSearchService:
        return InMemoryReleaseSearchService()

    @cached_property
    def release_download_service(self) -> InMemoryReleaseDownloadService:
        return InMemoryReleaseDownloadService()

    @cached_property
    def log_reader(self) -> LogFileReader:
        return LogFileReader(self.settings.log_file)

    @cached_property
    def list_logs_query(self) -> ListLogsQuery:
        return ListLogsQuery(reader=self.log_reader, settings=self.settings)

    @cached_property
    def list_logs_use_case(self) -> ListLogsUseCase:
        return ListLogsUseCase(query=self.list_logs_query)

    @cached_property
    def release_summary_query(self) -> ReleaseSummaryQuery:
        return ReleaseSummaryQuery(db=self.db_manager)


@lru_cache(maxsize=1)
def get_container() -> AppContainer:
    """Return the singleton application container."""

    settings = get_settings()
    return AppContainer(settings=settings)
