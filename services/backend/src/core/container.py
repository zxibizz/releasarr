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
from src.application.use_cases.auth import (
    AuthenticatePrincipalUseCase,
    BootstrapAdminUseCase,
    GetOrCreateServiceApiKeyUseCase,
    GetSetupStatusUseCase,
    LoginUseCase,
    LogoutUseCase,
    RefreshSessionUseCase,
    RegenerateServiceApiKeyUseCase,
    SessionIssuer,
)
from src.application.use_cases.discover.add_request import AddMediaRequestUseCase
from src.application.use_cases.discover.list_root_folders import ListRootFoldersUseCase
from src.application.use_cases.discover.list_season_options import ListSeasonOptionsUseCase
from src.application.use_cases.discover.manage_seasons import (
    ListRequestSeasonsUseCase,
    UpdateRequestSeasonsUseCase,
)
from src.application.use_cases.discover.search_media import SearchMediaUseCase
from src.application.use_cases.indexers.list_history import ListIndexerHistoryUseCase
from src.application.use_cases.indexers.list_indexers import ListIndexersUseCase
from src.application.use_cases.indexers.list_logs import ListIndexerLogsUseCase
from src.application.use_cases.indexers.run_indexer_tests import (
    RunAllIndexerTestsUseCase,
    RunIndexerTestUseCase,
)
from src.application.use_cases.logs.list_logs import ListLogsUseCase
from src.application.use_cases.releases.auto_mapping import ReleaseAutoMapper
from src.application.use_cases.releases.create_release import CreateReleaseUseCase
from src.application.use_cases.releases.delete_release import DeleteReleaseUseCase
from src.application.use_cases.releases.get_release import GetReleaseUseCase
from src.application.use_cases.releases.list_releases import ListReleasesUseCase
from src.application.use_cases.releases.pause_release import PauseReleaseUseCase
from src.application.use_cases.releases.queue_manual_release import (
    QueueManualReleaseUseCase,
)
from src.application.use_cases.releases.queue_release_download import (
    QueueReleaseDownloadUseCase,
)
from src.application.use_cases.releases.replace_existing import ExistingReleaseReplacer
from src.application.use_cases.releases.resume_release import ResumeReleaseUseCase
from src.application.use_cases.releases.search_release_sources import (
    SearchReleaseSourcesUseCase,
)
from src.application.use_cases.releases.suggest_file_mappings import (
    SuggestReleaseFileMappingsUseCase,
)
from src.application.use_cases.releases.update_file_mappings import (
    UpdateReleaseFileMappingsUseCase,
)
from src.application.use_cases.releases.warnings import (
    ReleaseWarningEvaluator,
    RequestWarningSynchronizer,
)
from src.application.use_cases.requests.create_request import CreateMediaRequestUseCase
from src.application.use_cases.requests.delete_request import DeleteMediaRequestUseCase
from src.application.use_cases.requests.get_request import GetMediaRequestUseCase
from src.application.use_cases.requests.list_episodes import ListRequestEpisodesUseCase
from src.application.use_cases.requests.list_requests import ListMediaRequestsUseCase
from src.application.use_cases.requests.recompute_state import RecomputeRequestStateUseCase
from src.application.use_cases.requests.state import RequestStateDeriver
from src.application.use_cases.requests.sync_radarr import SyncRadarrMediaRequestsUseCase
from src.application.use_cases.requests.sync_sonarr import SyncSonarrMediaRequestsUseCase
from src.application.use_cases.requests.update_request import UpdateMediaRequestUseCase
from src.application.use_cases.settings import (
    GetSettingsUseCase,
    ListDownloadCategoriesUseCase,
    ListIndexerCategoriesUseCase,
    ListQualityProfilesUseCase,
    TestIntegrationConnectionUseCase,
    UpdateSettingsSectionUseCase,
)
from src.application.use_cases.tasks.enqueue_sync import EnqueueSyncJobUseCase
from src.application.use_cases.tasks.get_sync_job import (
    GetSyncJobUseCase,
    ListScheduledTasksUseCase,
    ListSyncJobsUseCase,
)
from src.application.use_cases.tasks.update_interval import UpdateTaskIntervalUseCase
from src.application.use_cases.users import (
    ChangePasswordUseCase,
    CreateUserUseCase,
    DeleteUserUseCase,
    GetUserUseCase,
    ListUsersUseCase,
    UpdateUserUseCase,
)
from src.core.logging import configure_logging, logger
from src.db.session import DBManager, get_db_manager
from src.domain.enums import LogService
from src.infrastructure.auth import (
    Argon2PasswordHasher,
    JwtAccessTokenCodec,
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemyServiceApiKeyRepository,
)
from src.infrastructure.logs import LogFileReader
from src.infrastructure.media_requests import SqlAlchemyMediaRequestRepository
from src.infrastructure.prowlarr import ProwlarrIndexerDirectory, ProwlarrReleaseSearchService
from src.infrastructure.qbittorrent import (
    QbittorrentClient,
    QbittorrentReleaseDownloadService,
    QbittorrentReleaseLifecycleService,
)
from src.infrastructure.radarr import RadarrHttpClient
from src.infrastructure.releases import SqlAlchemyReleaseRepository
from src.infrastructure.request_warnings import SqlAlchemyRequestWarningRepository
from src.infrastructure.settings import LayeredSettingsProvider, SqlAlchemyAppSettingsRepository
from src.infrastructure.sonarr import SonarrHttpClient
from src.infrastructure.sync_jobs import (
    SqlAlchemyScheduledTaskRepository,
    SqlAlchemySyncJobRepository,
)
from src.infrastructure.tmdb import TmdbHttpClient
from src.infrastructure.tvdb import TvdbHttpClient
from src.infrastructure.users import SqlAlchemyUserRepository
from src.settings.config import AppSettings, get_settings

if TYPE_CHECKING:
    from src.application.use_cases.releases.export_finished import ExportFinishedReleasesUseCase
    from src.application.use_cases.releases.refresh_request_releases import (
        RefreshRequestReleasesUseCase,
    )
    from src.application.use_cases.releases.regrab import ReleaseRegrapper
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

    @cached_property
    def request_warnings(self) -> SqlAlchemyRequestWarningRepository:
        return SqlAlchemyRequestWarningRepository(db=self._container.db_manager)

    @cached_property
    def sync_jobs(self) -> SqlAlchemySyncJobRepository:
        return SqlAlchemySyncJobRepository(db=self._container.db_manager)

    @cached_property
    def scheduled_tasks(self) -> SqlAlchemyScheduledTaskRepository:
        return SqlAlchemyScheduledTaskRepository(db=self._container.db_manager)

    @cached_property
    def users(self) -> SqlAlchemyUserRepository:
        return SqlAlchemyUserRepository(db=self._container.db_manager)

    @cached_property
    def refresh_tokens(self) -> SqlAlchemyRefreshTokenRepository:
        return SqlAlchemyRefreshTokenRepository(db=self._container.db_manager)

    @cached_property
    def service_api_keys(self) -> SqlAlchemyServiceApiKeyRepository:
        return SqlAlchemyServiceApiKeyRepository(db=self._container.db_manager)

    @cached_property
    def app_settings(self) -> SqlAlchemyAppSettingsRepository:
        return SqlAlchemyAppSettingsRepository(db=self._container.db_manager)


@dataclass
class ServiceContainer:
    _container: AppContainer

    @cached_property
    def password_hasher(self) -> Argon2PasswordHasher:
        return Argon2PasswordHasher()

    @cached_property
    def access_token_codec(self) -> JwtAccessTokenCodec:
        return JwtAccessTokenCodec(secret=self._container.settings.auth_secret.get_secret_value())

    @cached_property
    def release_lifecycle(self) -> ReleaseLifecycleService:
        return QbittorrentReleaseLifecycleService(client=self.qbittorrent_client)

    @cached_property
    def release_search(self) -> ReleaseSearchService:
        settings = self._container.settings
        return ProwlarrReleaseSearchService(
            base_url=settings.prowlarr_url,
            api_key=settings.prowlarr_api_key.get_secret_value(),
            timeout_seconds=settings.prowlarr_timeout,
            categories=settings.prowlarr_categories,
        )

    @cached_property
    def indexer_directory(self) -> ProwlarrIndexerDirectory:
        """Prowlarr's indexer view, whether or not Prowlarr is set up.

        Built regardless, so a caller has one type to handle and asks it whether
        it can work: an absent object would push the same question onto every
        call site, one `if` at a time.
        """

        settings = self._container.settings
        return ProwlarrIndexerDirectory(
            base_url=settings.prowlarr_url,
            api_key=settings.prowlarr_api_key.get_secret_value(),
            timeout_seconds=settings.prowlarr_timeout,
        )

    @cached_property
    def release_download(self) -> ReleaseDownloadService:
        settings = self._container.settings
        return QbittorrentReleaseDownloadService(
            client=self.qbittorrent_client,
            save_path=settings.qbittorrent_save_path,
            category=settings.qbittorrent_category,
            tag_prefix=settings.qbittorrent_tag_prefix,
            paused=settings.qbittorrent_paused,
        )

    @cached_property
    def qbittorrent_client(self) -> QbittorrentClient:
        """Single shared qBittorrent client, whether or not it is set up.

        Nothing stands in when the settings are incomplete: a stand-in cannot
        download, and pretending otherwise turned a misconfigured deployment into
        one that silently reported success. `is_configured` is what callers read
        instead.
        """

        settings = self._container.settings
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
    def radarr(self) -> RadarrHttpClient:
        settings = self._container.settings
        return RadarrHttpClient(
            base_url=settings.radarr_url,
            api_key=settings.radarr_api_key.get_secret_value(),
        )

    @cached_property
    def tvdb(self) -> TvdbHttpClient:
        settings = self._container.settings
        return TvdbHttpClient(
            base_url=settings.tvdb_base_url,
            api_token=settings.tvdb_api_key.get_secret_value(),
        )

    @cached_property
    def tmdb(self) -> TmdbHttpClient:
        settings = self._container.settings
        return TmdbHttpClient(
            base_url=settings.tmdb_base_url,
            api_token=settings.tmdb_api_key.get_secret_value(),
        )


@dataclass
class QueryContainer:
    _container: AppContainer

    @cached_property
    def logs(self) -> ListLogsQuery:
        return ListLogsQuery(
            reader=self._container.infrastructure.log_reader, settings=self._container.settings
        )


@dataclass
class UseCaseContainer:
    _container: AppContainer

    @cached_property
    def auth(self) -> AuthUseCases:
        return AuthUseCases(self._container)

    @cached_property
    def users(self) -> UserUseCases:
        return UserUseCases(self._container)

    @cached_property
    def discover(self) -> DiscoverUseCases:
        return DiscoverUseCases(self._container)

    @cached_property
    def indexers(self) -> IndexerUseCases:
        return IndexerUseCases(self._container)

    @cached_property
    def logs(self) -> LogUseCases:
        return LogUseCases(self._container)

    @cached_property
    def media_requests(self) -> MediaRequestUseCases:
        return MediaRequestUseCases(self._container)

    @cached_property
    def releases(self) -> ReleaseUseCases:
        return ReleaseUseCases(self._container)

    @cached_property
    def tasks(self) -> TaskUseCases:
        return TaskUseCases(self._container)

    @cached_property
    def settings(self) -> SettingsUseCases:
        return SettingsUseCases(self._container)


@dataclass
class AuthUseCases:
    _container: AppContainer

    @cached_property
    def _session_issuer(self) -> SessionIssuer:
        settings = self._container.settings
        return SessionIssuer(
            refresh_tokens=self._container.repositories.refresh_tokens,
            access_tokens=self._container.services.access_token_codec,
            access_token_ttl_seconds=settings.auth_access_token_ttl_seconds,
            session_ttl_seconds=settings.auth_refresh_token_ttl_seconds,
            remember_ttl_seconds=settings.auth_refresh_remember_ttl_seconds,
        )

    @cached_property
    def login(self) -> LoginUseCase:
        settings = self._container.settings
        return LoginUseCase(
            users=self._container.repositories.users,
            password_hasher=self._container.services.password_hasher,
            session_issuer=self._session_issuer,
            max_failed_logins=settings.auth_max_failed_logins,
            lockout_seconds=settings.auth_lockout_seconds,
        )

    @cached_property
    def refresh(self) -> RefreshSessionUseCase:
        settings = self._container.settings
        return RefreshSessionUseCase(
            users=self._container.repositories.users,
            refresh_tokens=self._container.repositories.refresh_tokens,
            session_issuer=self._session_issuer,
            reuse_grace_seconds=settings.auth_refresh_reuse_grace_seconds,
        )

    @cached_property
    def logout(self) -> LogoutUseCase:
        return LogoutUseCase(refresh_tokens=self._container.repositories.refresh_tokens)

    @cached_property
    def authenticate(self) -> AuthenticatePrincipalUseCase:
        return AuthenticatePrincipalUseCase(
            users=self._container.repositories.users,
            service_api_keys=self._container.repositories.service_api_keys,
            access_tokens=self._container.services.access_token_codec,
        )

    @cached_property
    def bootstrap_admin(self) -> BootstrapAdminUseCase:
        return BootstrapAdminUseCase(
            users=self._container.repositories.users,
            password_hasher=self._container.services.password_hasher,
            session_issuer=self._session_issuer,
        )

    @cached_property
    def setup_status(self) -> GetSetupStatusUseCase:
        return GetSetupStatusUseCase(users=self._container.repositories.users)

    @cached_property
    def service_key(self) -> GetOrCreateServiceApiKeyUseCase:
        return GetOrCreateServiceApiKeyUseCase(
            service_api_keys=self._container.repositories.service_api_keys
        )

    @cached_property
    def regenerate_service_key(self) -> RegenerateServiceApiKeyUseCase:
        return RegenerateServiceApiKeyUseCase(
            service_api_keys=self._container.repositories.service_api_keys
        )


@dataclass
class UserUseCases:
    _container: AppContainer

    @cached_property
    def list(self) -> ListUsersUseCase:
        return ListUsersUseCase(users=self._container.repositories.users)

    @cached_property
    def get(self) -> GetUserUseCase:
        return GetUserUseCase(users=self._container.repositories.users)

    @cached_property
    def create(self) -> CreateUserUseCase:
        return CreateUserUseCase(
            users=self._container.repositories.users,
            password_hasher=self._container.services.password_hasher,
        )

    @cached_property
    def update(self) -> UpdateUserUseCase:
        return UpdateUserUseCase(
            users=self._container.repositories.users,
            password_hasher=self._container.services.password_hasher,
        )

    @cached_property
    def delete(self) -> DeleteUserUseCase:
        return DeleteUserUseCase(users=self._container.repositories.users)

    @cached_property
    def change_password(self) -> ChangePasswordUseCase:
        return ChangePasswordUseCase(
            users=self._container.repositories.users,
            password_hasher=self._container.services.password_hasher,
        )


@dataclass
class IndexerUseCases:
    _container: AppContainer

    @cached_property
    def list(self) -> ListIndexersUseCase:
        return ListIndexersUseCase(directory=self._container.services.indexer_directory)

    @cached_property
    def list_history(self) -> ListIndexerHistoryUseCase:
        return ListIndexerHistoryUseCase(
            directory=self._container.services.indexer_directory,
            settings=self._container.settings,
        )

    @cached_property
    def list_logs(self) -> ListIndexerLogsUseCase:
        return ListIndexerLogsUseCase(
            directory=self._container.services.indexer_directory,
            settings=self._container.settings,
        )

    @cached_property
    def run_test(self) -> RunIndexerTestUseCase:
        return RunIndexerTestUseCase(directory=self._container.services.indexer_directory)

    @cached_property
    def run_all_tests(self) -> RunAllIndexerTestsUseCase:
        return RunAllIndexerTestsUseCase(directory=self._container.services.indexer_directory)


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
            warning_repository=self._container.repositories.request_warnings,
            settings=self._container.settings,
        )

    @cached_property
    def create(self) -> CreateMediaRequestUseCase:
        return CreateMediaRequestUseCase(repository=self._container.repositories.media_requests)

    @cached_property
    def get(self) -> GetMediaRequestUseCase:
        return GetMediaRequestUseCase(
            repository=self._container.repositories.media_requests,
            warning_repository=self._container.repositories.request_warnings,
        )

    @cached_property
    def update(self) -> UpdateMediaRequestUseCase:
        return UpdateMediaRequestUseCase(repository=self._container.repositories.media_requests)

    @cached_property
    def delete(self) -> DeleteMediaRequestUseCase:
        return DeleteMediaRequestUseCase(
            repository=self._container.repositories.media_requests,
            sonarr_service=self._container.services.sonarr,
            radarr_service=self._container.services.radarr,
        )

    @cached_property
    def episodes(self) -> ListRequestEpisodesUseCase:
        return ListRequestEpisodesUseCase(
            repository=self._container.repositories.media_requests,
            sonarr_service=self._container.services.sonarr,
        )

    @cached_property
    def sync_sonarr(self) -> SyncSonarrMediaRequestsUseCase:
        return SyncSonarrMediaRequestsUseCase(
            repository=self._container.repositories.media_requests,
            sonarr_service=self._container.services.sonarr,
            tvdb_service=self._container.services.tvdb,
            recompute_state=self.recompute_state,
            metadata_languages=self._container.settings.metadata_languages,
        )

    @cached_property
    def sync_radarr(self) -> SyncRadarrMediaRequestsUseCase:
        return SyncRadarrMediaRequestsUseCase(
            repository=self._container.repositories.media_requests,
            radarr_service=self._container.services.radarr,
            tmdb_service=self._container.services.tmdb,
            recompute_state=self.recompute_state,
            metadata_languages=self._container.settings.metadata_languages,
        )

    @cached_property
    def request_state_deriver(self) -> RequestStateDeriver:
        return RequestStateDeriver()

    @cached_property
    def recompute_state(self) -> RecomputeRequestStateUseCase:
        return RecomputeRequestStateUseCase(
            repository=self._container.repositories.media_requests,
            release_repository=self._container.repositories.releases,
            warning_synchronizer=self._container.use_cases.releases.warning_synchronizer,
            deriver=self.request_state_deriver,
        )


@dataclass
class DiscoverUseCases:
    _container: AppContainer

    @cached_property
    def search(self) -> SearchMediaUseCase:
        return SearchMediaUseCase(
            repository=self._container.repositories.media_requests,
            sonarr_service=self._container.services.sonarr,
            radarr_service=self._container.services.radarr,
            tvdb_service=self._container.services.tvdb,
            tmdb_service=self._container.services.tmdb,
            metadata_languages=self._container.settings.metadata_languages,
        )

    @cached_property
    def season_options(self) -> ListSeasonOptionsUseCase:
        return ListSeasonOptionsUseCase(
            repository=self._container.repositories.media_requests,
            sonarr_service=self._container.services.sonarr,
            tvdb_service=self._container.services.tvdb,
            metadata_languages=self._container.settings.metadata_languages,
        )

    @cached_property
    def root_folders(self) -> ListRootFoldersUseCase:
        return ListRootFoldersUseCase(
            sonarr_service=self._container.services.sonarr,
            radarr_service=self._container.services.radarr,
        )

    @cached_property
    def request_seasons(self) -> ListRequestSeasonsUseCase:
        return ListRequestSeasonsUseCase(
            repository=self._container.repositories.media_requests,
            sonarr_service=self._container.services.sonarr,
        )

    @cached_property
    def update_request_seasons(self) -> UpdateRequestSeasonsUseCase:
        return UpdateRequestSeasonsUseCase(
            repository=self._container.repositories.media_requests,
            sonarr_service=self._container.services.sonarr,
            sync_sonarr=self._container.use_cases.media_requests.sync_sonarr,
        )

    @cached_property
    def add_request(self) -> AddMediaRequestUseCase:
        settings = self._container.settings
        media_requests = self._container.use_cases.media_requests
        return AddMediaRequestUseCase(
            repository=self._container.repositories.media_requests,
            sonarr_service=self._container.services.sonarr,
            radarr_service=self._container.services.radarr,
            sync_sonarr=media_requests.sync_sonarr,
            sync_radarr=media_requests.sync_radarr,
            sonarr_quality_profile_id=settings.sonarr_quality_profile_id,
            radarr_quality_profile_id=settings.radarr_quality_profile_id,
        )


@dataclass
class ReleaseUseCases:
    _container: AppContainer

    @cached_property
    def list(self) -> ListReleasesUseCase:
        return ListReleasesUseCase(
            repository=self._container.repositories.releases,
            warning_repository=self._container.repositories.request_warnings,
            settings=self._container.settings,
        )

    @cached_property
    def create(self) -> CreateReleaseUseCase:
        return CreateReleaseUseCase(
            repository=self._container.repositories.releases,
            recompute_state=self._container.use_cases.media_requests.recompute_state,
        )

    @cached_property
    def get(self) -> GetReleaseUseCase:
        return GetReleaseUseCase(
            repository=self._container.repositories.releases,
            warning_repository=self._container.repositories.request_warnings,
        )

    @cached_property
    def delete(self) -> DeleteReleaseUseCase:
        return DeleteReleaseUseCase(
            repository=self._container.repositories.releases,
            download_service=self._container.services.release_download,
            warning_repository=self._container.repositories.request_warnings,
            recompute_state=self._container.use_cases.media_requests.recompute_state,
        )

    @cached_property
    def update_mappings(self) -> UpdateReleaseFileMappingsUseCase:
        return UpdateReleaseFileMappingsUseCase(
            repository=self._container.repositories.releases,
            warning_repository=self._container.repositories.request_warnings,
            enqueue_sync=self._container.use_cases.tasks.enqueue_sync,
            recompute_state=self._container.use_cases.media_requests.recompute_state,
        )

    @cached_property
    def suggest_mappings(self) -> SuggestReleaseFileMappingsUseCase:
        return SuggestReleaseFileMappingsUseCase(
            repository=self._container.repositories.releases,
            auto_mapper=self.auto_mapper,
        )

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
        settings = self._container.settings
        return SearchReleaseSourcesUseCase(
            search_service=self._container.services.release_search,
            directory=self._container.services.indexer_directory,
            timeout_seconds=settings.prowlarr_search_timeout,
            retries=settings.prowlarr_search_retries,
            concurrency=settings.prowlarr_search_concurrency,
        )

    @cached_property
    def auto_mapper(self) -> ReleaseAutoMapper:
        from src.application.utility.file_matcher import ReleaseFileMatcher

        return ReleaseAutoMapper(
            repository=self._container.repositories.releases,
            file_matcher=ReleaseFileMatcher(),
            request_repository=self._container.repositories.media_requests,
        )

    @cached_property
    def warning_evaluator(self) -> ReleaseWarningEvaluator:
        return ReleaseWarningEvaluator()

    @cached_property
    def warning_synchronizer(self) -> RequestWarningSynchronizer:
        return RequestWarningSynchronizer(
            repository=self._container.repositories.releases,
            warning_repository=self._container.repositories.request_warnings,
            evaluator=self.warning_evaluator,
        )

    @cached_property
    def existing_release_replacer(self) -> ExistingReleaseReplacer:
        return ExistingReleaseReplacer(
            repository=self._container.repositories.releases,
            download_service=self._container.services.release_download,
            warning_repository=self._container.repositories.request_warnings,
            recompute_state=self._container.use_cases.media_requests.recompute_state,
        )

    @cached_property
    def queue_download(self) -> QueueReleaseDownloadUseCase:
        return QueueReleaseDownloadUseCase(
            repository=self._container.repositories.releases,
            download_service=self._container.services.release_download,
            search_service=self._container.services.release_search,
            auto_mapper=self.auto_mapper,
            existing_release_replacer=self.existing_release_replacer,
            recompute_state=self._container.use_cases.media_requests.recompute_state,
        )

    @cached_property
    def queue_manual(self) -> QueueManualReleaseUseCase:
        return QueueManualReleaseUseCase(
            repository=self._container.repositories.releases,
            download_service=self._container.services.release_download,
            auto_mapper=self.auto_mapper,
            existing_release_replacer=self.existing_release_replacer,
            recompute_state=self._container.use_cases.media_requests.recompute_state,
        )

    @cached_property
    def export_finished(self) -> ExportFinishedReleasesUseCase:
        from src.application.use_cases.releases.export_finished import (
            ExportFinishedReleasesUseCase,
        )

        return ExportFinishedReleasesUseCase(
            repository=self._container.repositories.releases,
            sonarr=self._container.services.sonarr,
            radarr=self._container.services.radarr,
            auto_mapper=self.auto_mapper,
            download_service=self._container.services.release_download,
            request_repository=self._container.repositories.media_requests,
            recompute_state=self._container.use_cases.media_requests.recompute_state,
        )

    @cached_property
    def regrab_outdated(self) -> RegrabOutdatedReleasesUseCase:
        from src.application.use_cases.releases.regrab_outdated import RegrabOutdatedReleasesUseCase

        return RegrabOutdatedReleasesUseCase(
            repository=self._container.repositories.releases,
            search_service=self._container.services.release_search,
            download_service=self._container.services.release_download,
            auto_mapper=self.auto_mapper,
            directory=self._container.services.indexer_directory,
            warning_repository=self._container.repositories.request_warnings,
            recompute_state=self._container.use_cases.media_requests.recompute_state,
            max_per_indexer=self._container.settings.max_regrabs_per_indexer_per_execution,
            indexer_delay_seconds=self._container.settings.regrab_indexer_delay_seconds,
        )

    @cached_property
    def regrapper(self) -> ReleaseRegrapper:
        """The per-release re-grab check, on its own so a request can drive it."""

        from src.application.use_cases.releases.regrab import ReleaseRegrapper

        return ReleaseRegrapper(
            repository=self._container.repositories.releases,
            search_service=self._container.services.release_search,
            download_service=self._container.services.release_download,
            auto_mapper=self.auto_mapper,
            directory=self._container.services.indexer_directory,
            warning_repository=self._container.repositories.request_warnings,
            recompute_state=self._container.use_cases.media_requests.recompute_state,
        )

    @cached_property
    def refresh_request(self) -> RefreshRequestReleasesUseCase:
        from src.application.use_cases.releases.refresh_request_releases import (
            RefreshRequestReleasesUseCase,
        )

        return RefreshRequestReleasesUseCase(
            request_repository=self._container.repositories.media_requests,
            release_repository=self._container.repositories.releases,
            warning_repository=self._container.repositories.request_warnings,
            download_service=self._container.services.release_download,
            search_service=self._container.services.release_search,
            regrapper=self.regrapper,
            recompute_state=self._container.use_cases.media_requests.recompute_state,
        )


@dataclass
class TaskUseCases:
    _container: AppContainer

    @cached_property
    def enqueue_sync(self) -> EnqueueSyncJobUseCase:
        return EnqueueSyncJobUseCase(repository=self._container.repositories.sync_jobs)

    @cached_property
    def get_sync_job(self) -> GetSyncJobUseCase:
        return GetSyncJobUseCase(repository=self._container.repositories.sync_jobs)

    @cached_property
    def list_sync_jobs(self) -> ListSyncJobsUseCase:
        return ListSyncJobsUseCase(repository=self._container.repositories.sync_jobs)

    @cached_property
    def list_scheduled_tasks(self) -> ListScheduledTasksUseCase:
        return ListScheduledTasksUseCase(repository=self._container.repositories.scheduled_tasks)

    @cached_property
    def update_interval(self) -> UpdateTaskIntervalUseCase:
        return UpdateTaskIntervalUseCase(repository=self._container.repositories.scheduled_tasks)


@dataclass
class SettingsUseCases:
    _container: AppContainer

    @cached_property
    def get(self) -> GetSettingsUseCase:
        return GetSettingsUseCase(provider=self._container.settings_provider)

    @cached_property
    def update_section(self) -> UpdateSettingsSectionUseCase:
        return UpdateSettingsSectionUseCase(
            repository=self._container.repositories.app_settings,
            provider=self._container.settings_provider,
        )

    @cached_property
    def test_connection(self) -> TestIntegrationConnectionUseCase:
        return TestIntegrationConnectionUseCase(settings=self._container.settings)

    @cached_property
    def list_quality_profiles(self) -> ListQualityProfilesUseCase:
        return ListQualityProfilesUseCase(
            sonarr_service=self._container.services.sonarr,
            radarr_service=self._container.services.radarr,
        )

    @cached_property
    def list_indexer_categories(self) -> ListIndexerCategoriesUseCase:
        return ListIndexerCategoriesUseCase(directory=self._container.services.indexer_directory)

    @cached_property
    def list_download_categories(self) -> ListDownloadCategoriesUseCase:
        return ListDownloadCategoriesUseCase(client=self._container.services.qbittorrent_client)


@dataclass
class InfrastructureContainer:
    _container: AppContainer

    @cached_property
    def log_reader(self) -> LogFileReader:
        settings = self._container.settings
        return LogFileReader(
            {
                LogService.API.value: settings.log_file,
                LogService.SCHEDULER.value: settings.scheduler_log_file,
            },
            history_files=settings.log_history_files,
        )


@dataclass(init=False)
class AppContainer:
    # The env/.env layer. Stored overrides layer on top via ``settings_provider``;
    # ``settings`` resolves to the effective composition of the two.
    _env_settings: AppSettings

    def __init__(self, settings: AppSettings) -> None:
        self._env_settings = settings
        self._log_service: LogService = LogService.API
        # Old service containers awaiting close, retired one refresh after a
        # settings change so an in-flight request keeps its references.
        self._retired_services: list[ServiceContainer] = []

    @property
    def settings(self) -> AppSettings:
        return self.settings_provider.current()

    @cached_property
    def settings_provider(self) -> LayeredSettingsProvider:
        return LayeredSettingsProvider(self.repositories.app_settings, self._env_settings)

    def startup(self, *, service: LogService) -> None:
        """Hook for initializing resources (e.g. db engine, http clients).

        ``service`` is passed through to logging, which stamps every record with
        the process that wrote it. Logging and the auth-secret check run against
        the env layer: both are part of process identity, not something a stored
        override can reach before the first DB read.
        """

        self._log_service = service
        configure_logging(self._env_settings, service=service)
        if not self._env_settings.auth_secret.get_secret_value():
            # A blank signing secret would mean any deployment's tokens are
            # forgeable from the (public) source, not merely misconfigured.
            raise RuntimeError("RELEASARR_AUTH_SECRET must be set to a non-empty value")
        return None

    async def apply_settings_updates(self) -> bool:
        """Reload stored overrides when their revision moved, rebuilding clients.

        Cheap when nothing changed (one revision read per provider interval), so
        the API middleware and the scheduler loops call it freely. On a change the
        resolved settings swap, logging is re-applied for a new level, and the
        service and use-case caches are dropped so the next resolve builds clients
        from the new settings.
        """

        try:
            changed = await self.settings_provider.refresh_if_stale()
        except Exception as exc:
            # A settings read failing must not 500 an otherwise-served request.
            # A missing table before migrations is the common case; log it low.
            logger.debug("Settings refresh skipped: {error}", error=str(exc))
            changed = False

        # Close containers retired by the previous change; by now nothing that
        # was in flight then is still holding them.
        retired, self._retired_services = self._retired_services, []
        for old in retired:
            await self._close_services(old)

        if not changed:
            return False

        configure_logging(self.settings, service=self._log_service)

        old_services = self.__dict__.pop("services", None)
        if old_services is not None:
            self._retired_services.append(old_services)
        # Use cases captured service references at resolve time, so they are
        # rebuilt from the fresh service container too.
        self.__dict__.pop("use_cases", None)
        return True

    async def _close_services(self, services: ServiceContainer) -> None:
        client = services.__dict__.get("qbittorrent_client")
        if client is not None:
            await client.close()
        for key in ("tvdb", "tmdb", "sonarr", "radarr", "release_search", "indexer_directory"):
            service = services.__dict__.get(key)
            if service is not None and hasattr(service, "aclose"):
                await service.aclose()

    async def shutdown(self) -> None:
        """Hook for disposing resources during application shutdown."""

        for retired in self._retired_services:
            await self._close_services(retired)
        self._retired_services = []

        services = self.__dict__.get("services")
        if services is not None:
            await self._close_services(services)

        # Both sinks are enqueued, so records still in the queue are lost unless
        # the writer thread is given the chance to drain. The scheduler reaches
        # this through its own shutdown, so one flush covers both processes.
        await logger.complete()

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
