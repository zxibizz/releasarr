"""Application composition root.

The container keeps references to shared infrastructure (settings, db, clients).
Phase 0 stubs out the lifecycle hooks so later phases can populate them without
changing the FastAPI entrypoint signature.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property, lru_cache
from typing import TYPE_CHECKING

from src.application.interfaces.releases import (
    ReleaseDownloadService,
    ReleaseLifecycleService,
    ReleaseSearchService,
)
from src.application.queries.logs import ListLogsQuery
from src.application.queries.releases import ReleaseSummaryQuery
from src.application.use_cases.logs.list_logs import ListLogsUseCase
from src.application.use_cases.releases.create_release import CreateReleaseUseCase
from src.application.use_cases.releases.delete_release import DeleteReleaseUseCase
from src.application.use_cases.releases.get_release import GetReleaseUseCase
from src.application.use_cases.releases.list_releases import ListReleasesUseCase
from src.application.use_cases.releases.pause_release import PauseReleaseUseCase
from src.application.use_cases.releases.queue_release_download import (
    QueueReleaseDownloadUseCase,
)
from src.application.use_cases.releases.resume_release import ResumeReleaseUseCase
from src.application.use_cases.releases.search_release_sources import (
    SearchReleaseSourcesUseCase,
)
from src.application.use_cases.releases.update_file_mappings import (
    UpdateReleaseFileMappingsUseCase,
)
from src.application.use_cases.requests.create_request import CreateMediaRequestUseCase
from src.application.use_cases.requests.delete_request import DeleteMediaRequestUseCase
from src.application.use_cases.requests.get_request import GetMediaRequestUseCase
from src.application.use_cases.requests.list_requests import ListMediaRequestsUseCase
from src.application.use_cases.requests.sync_sonarr import SyncSonarrMediaRequestsUseCase
from src.application.use_cases.requests.update_request import UpdateMediaRequestUseCase
from src.core.logging import configure_logging
from src.db.session import DBManager, get_db_manager
from src.infrastructure.logs import LogFileReader
from src.infrastructure.media_requests import SqlAlchemyMediaRequestRepository
from src.infrastructure.prowlarr import ProwlarrReleaseSearchService
from src.infrastructure.qbittorrent import (
    QbittorrentClient,
    QbittorrentReleaseDownloadService,
    QbittorrentReleaseLifecycleService,
)
from src.infrastructure.releases import (
    InMemoryReleaseDownloadService,
    InMemoryReleaseLifecycleService,
    InMemoryReleaseSearchService,
    SqlAlchemyReleaseRepository,
)
from src.infrastructure.sonarr import SonarrHttpClient
from src.infrastructure.tvdb import TvdbHttpClient
from src.settings.config import AppSettings, get_settings

if TYPE_CHECKING:
    from src.application.use_cases.releases.export_finished import ExportFinishedSeriesUseCase
    from src.application.use_cases.releases.regrab_outdated import RegrabOutdatedReleasesUseCase


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
    def release_lifecycle(self) -> ReleaseLifecycleService:
        client = self.qbittorrent_client
        if client is not None:
            return QbittorrentReleaseLifecycleService(client=client)
        return InMemoryReleaseLifecycleService()

    @cached_property
    def release_search(self) -> ReleaseSearchService:
        settings = self._container.settings
        if settings.prowlarr_url and settings.prowlarr_api_key.get_secret_value():
            return ProwlarrReleaseSearchService(
                base_url=settings.prowlarr_url,
                api_key=settings.prowlarr_api_key.get_secret_value(),
                timeout_seconds=settings.prowlarr_timeout,
                categories=settings.prowlarr_categories,
            )
        return InMemoryReleaseSearchService()

    @cached_property
    def release_download(self) -> ReleaseDownloadService:
        settings = self._container.settings
        client = self.qbittorrent_client
        if client is not None:
            return QbittorrentReleaseDownloadService(
                client=client,
                save_path=settings.qbittorrent_save_path,
                category=settings.qbittorrent_category,
                tag_prefix=settings.qbittorrent_tag_prefix,
                paused=settings.qbittorrent_paused,
            )
        return InMemoryReleaseDownloadService()

    @cached_property
    def qbittorrent_client(self) -> QbittorrentClient | None:
        """Single shared qBittorrent client, or None when not configured."""

        settings = self._container.settings
        if not (
            settings.qbittorrent_url
            and settings.qbittorrent_username
            and settings.qbittorrent_password.get_secret_value()
        ):
            return None
        return QbittorrentClient(
            base_url=settings.qbittorrent_url,
            username=settings.qbittorrent_username,
            password=settings.qbittorrent_password.get_secret_value(),
            timeout=settings.qbittorrent_timeout,
        )

    @cached_property
    def sonarr(self) -> SonarrHttpClient:
        settings = self._container.settings
        return SonarrHttpClient(
            base_url=settings.sonarr_url,
            api_key=settings.sonarr_api_key.get_secret_value(),
        )

    @cached_property
    def tvdb(self) -> TvdbHttpClient | None:
        settings = self._container.settings
        if not settings.tvdb_api_key.get_secret_value():
            return None
        return TvdbHttpClient(
            base_url=settings.tvdb_base_url,
            api_token=settings.tvdb_api_key.get_secret_value(),
        )


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
        return ReleaseSummaryQuery(repository=self._container.repositories.releases)


@dataclass
class UseCaseContainer:
    _container: AppContainer

    @cached_property
    def logs(self) -> LogUseCases:
        return LogUseCases(self._container)

    @cached_property
    def media_requests(self) -> MediaRequestUseCases:
        return MediaRequestUseCases(self._container)

    @cached_property
    def releases(self) -> ReleaseUseCases:
        return ReleaseUseCases(self._container)


@dataclass
class LogUseCases:
    _container: AppContainer

    @cached_property
    def list(self) -> ListLogsUseCase:
        return ListLogsUseCase(query=self._container.queries.logs)


@dataclass
class MediaRequestUseCases:
    _container: AppContainer

    @cached_property
    def list(self) -> ListMediaRequestsUseCase:
        return ListMediaRequestsUseCase(
            repository=self._container.repositories.media_requests,
            settings=self._container.settings,
        )

    @cached_property
    def create(self) -> CreateMediaRequestUseCase:
        return CreateMediaRequestUseCase(repository=self._container.repositories.media_requests)

    @cached_property
    def get(self) -> GetMediaRequestUseCase:
        return GetMediaRequestUseCase(repository=self._container.repositories.media_requests)

    @cached_property
    def update(self) -> UpdateMediaRequestUseCase:
        return UpdateMediaRequestUseCase(repository=self._container.repositories.media_requests)

    @cached_property
    def delete(self) -> DeleteMediaRequestUseCase:
        return DeleteMediaRequestUseCase(repository=self._container.repositories.media_requests)

    @cached_property
    def sync_sonarr(self) -> SyncSonarrMediaRequestsUseCase:
        return SyncSonarrMediaRequestsUseCase(
            repository=self._container.repositories.media_requests,
            sonarr_service=self._container.services.sonarr,
            tvdb_service=self._container.services.tvdb,
            metadata_languages=self._container.settings.metadata_languages,
        )


@dataclass
class ReleaseUseCases:
    _container: AppContainer

    @cached_property
    def list(self) -> ListReleasesUseCase:
        return ListReleasesUseCase(
            repository=self._container.repositories.releases,
            settings=self._container.settings,
        )

    @cached_property
    def create(self) -> CreateReleaseUseCase:
        return CreateReleaseUseCase(repository=self._container.repositories.releases)

    @cached_property
    def get(self) -> GetReleaseUseCase:
        return GetReleaseUseCase(repository=self._container.repositories.releases)

    @cached_property
    def delete(self) -> DeleteReleaseUseCase:
        return DeleteReleaseUseCase(
            repository=self._container.repositories.releases,
            download_service=self._container.services.release_download,
        )

    @cached_property
    def update_mappings(self) -> UpdateReleaseFileMappingsUseCase:
        return UpdateReleaseFileMappingsUseCase(repository=self._container.repositories.releases)

    @cached_property
    def pause(self) -> PauseReleaseUseCase:
        return PauseReleaseUseCase(
            repository=self._container.repositories.releases,
            lifecycle_service=self._container.services.release_lifecycle,
        )

    @cached_property
    def resume(self) -> ResumeReleaseUseCase:
        return ResumeReleaseUseCase(
            repository=self._container.repositories.releases,
            lifecycle_service=self._container.services.release_lifecycle,
        )

    @cached_property
    def search_sources(self) -> SearchReleaseSourcesUseCase:
        return SearchReleaseSourcesUseCase(search_service=self._container.services.release_search)

    @cached_property
    def queue_download(self) -> QueueReleaseDownloadUseCase:
        return QueueReleaseDownloadUseCase(
            repository=self._container.repositories.releases,
            download_service=self._container.services.release_download,
            search_service=self._container.services.release_search,
            request_repository=self._container.repositories.media_requests,
        )

    @cached_property
    def export_finished(self) -> ExportFinishedSeriesUseCase:
        from src.application.use_cases.releases.export_finished import ExportFinishedSeriesUseCase
        from src.application.utility.file_matcher import ReleaseFileMatcher

        return ExportFinishedSeriesUseCase(
            repository=self._container.repositories.releases,
            sonarr=self._container.services.sonarr,
            file_matcher=ReleaseFileMatcher(),
        )

    @cached_property
    def regrab_outdated(self) -> RegrabOutdatedReleasesUseCase:
        from src.application.use_cases.releases.regrab_outdated import RegrabOutdatedReleasesUseCase

        return RegrabOutdatedReleasesUseCase(
            repository=self._container.repositories.releases,
            search_service=self._container.services.release_search,
            download_service=self._container.services.release_download,
        )


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

    async def shutdown(self) -> None:
        """Hook for disposing resources during application shutdown."""

        if "services" not in self.__dict__:
            return

        services = self.__dict__["services"]

        # A single shared qBittorrent client backs both lifecycle and download.
        client = services.__dict__.get("qbittorrent_client")
        if client is not None:
            await client.close()

        # Close any resolved HTTP-backed services exposing an async close hook.
        for key in ("tvdb", "sonarr", "release_search"):
            service = services.__dict__.get(key)
            if service is not None and hasattr(service, "aclose"):
                await service.aclose()

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
