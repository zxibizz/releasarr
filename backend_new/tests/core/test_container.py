"""Tests for the application container wiring."""

from __future__ import annotations

from src.application.queries.logs import ListLogsQuery
from src.application.queries.releases import ReleaseSummaryQuery
from src.application.use_cases.logs.list_logs import ListLogsUseCase
from src.core.container import AppContainer, get_container
from src.infrastructure.logs import LogFileReader
from src.infrastructure.media_requests.repository import SqlAlchemyMediaRequestRepository
from src.infrastructure.releases.repository import SqlAlchemyReleaseRepository
from src.infrastructure.releases.services import (
    InMemoryReleaseDownloadService,
    InMemoryReleaseLifecycleService,
    InMemoryReleaseSearchService,
)


def test_get_container_returns_singleton() -> None:
    container_a = get_container()
    container_b = get_container()

    assert container_a is container_b
    assert isinstance(container_a, AppContainer)


def test_container_provides_singletons() -> None:
    container = get_container()

    media_repo = container.media_request_repository
    release_repo = container.release_repository
    lifecycle_service = container.release_lifecycle_service
    search_service = container.release_search_service
    download_service = container.release_download_service
    log_reader = container.log_reader
    logs_query = container.list_logs_query
    logs_use_case = container.list_logs_use_case
    release_summary_query = container.release_summary_query

    assert isinstance(media_repo, SqlAlchemyMediaRequestRepository)
    assert isinstance(release_repo, SqlAlchemyReleaseRepository)
    assert isinstance(lifecycle_service, InMemoryReleaseLifecycleService)
    assert isinstance(search_service, InMemoryReleaseSearchService)
    assert isinstance(download_service, InMemoryReleaseDownloadService)
    assert isinstance(log_reader, LogFileReader)
    assert isinstance(logs_query, ListLogsQuery)
    assert isinstance(logs_use_case, ListLogsUseCase)
    assert isinstance(release_summary_query, ReleaseSummaryQuery)

    # Ensure the same singleton is returned on subsequent resolves.
    assert media_repo is container.media_request_repository
    assert release_repo is container.release_repository
    assert lifecycle_service is container.release_lifecycle_service
    assert search_service is container.release_search_service
    assert download_service is container.release_download_service
    assert log_reader is container.log_reader
    assert logs_query is container.list_logs_query
    assert logs_use_case is container.list_logs_use_case
    assert release_summary_query is container.release_summary_query
