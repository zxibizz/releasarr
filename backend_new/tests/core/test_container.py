"""Tests for the application container wiring."""

from __future__ import annotations

from src.application.queries.logs import ListLogsQuery
from src.application.queries.releases import ReleaseSummaryQuery
from src.application.use_cases.logs.list_logs import ListLogsUseCase
from src.application.use_cases.releases.list_releases import ListReleasesUseCase
from src.application.use_cases.requests.list_requests import ListMediaRequestsUseCase
from src.core.container import AppContainer, get_container
from src.infrastructure.logs import LogFileReader
from src.infrastructure.media_requests.repository import SqlAlchemyMediaRequestRepository
from src.infrastructure.releases.repository import SqlAlchemyReleaseRepository
from src.infrastructure.prowlarr import ProwlarrReleaseSearchService
from src.infrastructure.releases.services import (
    InMemoryReleaseDownloadService,
    InMemoryReleaseLifecycleService,
    InMemoryReleaseSearchService,
)
from src.settings.config import AppSettings


def test_get_container_returns_singleton() -> None:
    container_a = get_container()
    container_b = get_container()

    assert container_a is container_b
    assert isinstance(container_a, AppContainer)


def test_container_provides_singletons() -> None:
    container = get_container()

    media_repo = container.repositories.media_requests
    release_repo = container.repositories.releases
    lifecycle_service = container.services.release_lifecycle
    search_service = container.services.release_search
    download_service = container.services.release_download
    log_reader = container.infrastructure.log_reader
    logs_query = container.queries.logs
    logs_use_case = container.use_cases.logs.list
    media_request_list = container.use_cases.media_requests.list
    release_list = container.use_cases.releases.list
    release_summary_query = container.queries.release_summary

    assert isinstance(media_repo, SqlAlchemyMediaRequestRepository)
    assert isinstance(release_repo, SqlAlchemyReleaseRepository)
    assert isinstance(lifecycle_service, InMemoryReleaseLifecycleService)
    assert isinstance(search_service, (ProwlarrReleaseSearchService, InMemoryReleaseSearchService))
    assert isinstance(download_service, InMemoryReleaseDownloadService)
    assert isinstance(log_reader, LogFileReader)
    assert isinstance(logs_query, ListLogsQuery)
    assert isinstance(logs_use_case, ListLogsUseCase)
    assert isinstance(media_request_list, ListMediaRequestsUseCase)
    assert isinstance(release_list, ListReleasesUseCase)
    assert isinstance(release_summary_query, ReleaseSummaryQuery)

    # Ensure the same singleton is returned on subsequent resolves.
    assert media_repo is container.repositories.media_requests
    assert release_repo is container.repositories.releases
    assert lifecycle_service is container.services.release_lifecycle
    assert search_service is container.services.release_search
    assert download_service is container.services.release_download
    assert log_reader is container.infrastructure.log_reader
    assert logs_query is container.queries.logs
    assert logs_use_case is container.use_cases.logs.list
    assert media_request_list is container.use_cases.media_requests.list
    assert release_list is container.use_cases.releases.list
    assert release_summary_query is container.queries.release_summary


def test_container_uses_prowlarr_search_when_configured() -> None:
    settings = AppSettings(
        prowlarr_url="https://prowlarr.example/api/v1",
        prowlarr_api_key="token",
    )
    container = AppContainer(settings=settings)

    search_service = container.services.release_search

    assert isinstance(search_service, ProwlarrReleaseSearchService)
