"""Tests for the application container wiring."""

from __future__ import annotations

from src.core.container import AppContainer, get_container
from src.application.queries.releases import ReleaseSummaryQuery
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


def test_container_resolves_dependencies() -> None:
    container = get_container()

    media_repo = container.resolve("media_request_repository")
    release_repo = container.resolve("release_repository")
    lifecycle_service = container.resolve("release_lifecycle_service")
    search_service = container.resolve("release_search_service")
    download_service = container.resolve("release_download_service")
    log_reader = container.resolve("log_reader")
    logs_query = container.resolve("list_logs_query")
    logs_use_case = container.resolve("list_logs_use_case")
    release_summary_query = container.resolve("release_summary_query")

    assert isinstance(media_repo, SqlAlchemyMediaRequestRepository)
    assert isinstance(release_repo, SqlAlchemyReleaseRepository)
    assert isinstance(lifecycle_service, InMemoryReleaseLifecycleService)
    assert isinstance(search_service, InMemoryReleaseSearchService)
    assert isinstance(download_service, InMemoryReleaseDownloadService)
    assert isinstance(log_reader, LogFileReader)

    from src.application.queries.logs import ListLogsQuery
    from src.application.use_cases.logs.list_logs import ListLogsUseCase

    assert isinstance(logs_query, ListLogsQuery)
    assert isinstance(logs_use_case, ListLogsUseCase)
    assert isinstance(release_summary_query, ReleaseSummaryQuery)

    # Ensure the same singleton is returned on subsequent resolves.
    assert media_repo is container.resolve("media_request_repository")
    assert release_repo is container.resolve("release_repository")
    assert lifecycle_service is container.resolve("release_lifecycle_service")
    assert search_service is container.resolve("release_search_service")
    assert download_service is container.resolve("release_download_service")
    assert log_reader is container.resolve("log_reader")
    assert logs_query is container.resolve("list_logs_query")
    assert logs_use_case is container.resolve("list_logs_use_case")
    assert release_summary_query is container.resolve("release_summary_query")


def test_resolve_unknown_component_raises() -> None:
    container = get_container()

    try:
        container.resolve("unknown")
    except LookupError as exc:
        assert "Component 'unknown'" in str(exc)
    else:  # pragma: no cover - defensive guard
        raise AssertionError("Expected LookupError to be raised")
