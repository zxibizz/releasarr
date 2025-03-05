from __future__ import annotations

from dataclasses import dataclass

from src.application.interfaces.db_manager import I_DBManager
from src.application.interfaces.release_searcher import I_ReleaseSearcher
from src.application.interfaces.releases_repository import I_ReleasesRepository
from src.application.interfaces.series_service import I_SeriesService
from src.application.interfaces.shows_repository import I_ShowsRepository
from src.application.interfaces.torrent_client import I_TorrentClient
from src.application.interfaces.tvdb_client import I_TvdbClient
from src.application.use_cases.releases.delete import UseCase_DeleteRelease
from src.application.use_cases.releases.export_finished_series import (
    UseCase_ExportFinishedSeries,
)
from src.application.use_cases.releases.grab import UseCase_GrabRelease
from src.application.use_cases.releases.import_torrent_stats import (
    UseCase_ImportReleasesTorrentStats,
)
from src.application.use_cases.releases.re_grab_outdated import (
    UseCase_ReGrabOutdatedReleases,
)
from src.application.use_cases.releases.search import UseCase_SearchReleases
from src.application.use_cases.releases.update_files_matching import (
    UseCase_UpdateReleaseFileMatching,
)
from src.application.use_cases.shows.sync_missing_series import (
    UseCase_SyncMissingSeries,
)
from src.application.utility.release_files_matchings_autocompleter import (
    ReleaseFileMatchingsAutocompleter,
)
from src.db import get_async_sessionmaker
from src.infrastructure.api_clients.prowlarr import ProwlarrApiClient
from src.infrastructure.api_clients.qbittorrent import QBittorrentApiClient
from src.infrastructure.api_clients.tvdb import TVDBApiClient
from src.infrastructure.db_manager import DBManager
from src.infrastructure.queries.get_show import Query_GetShow
from src.infrastructure.queries.list_shows import Query_ListShows
from src.infrastructure.repositories.releases import ReleasesRepository
from src.infrastructure.repositories.shows import ShowsRepository
from src.infrastructure.series_manager import SeriesService
from src.logger import logger
from src.settings import app_settings


@dataclass
class Dependencies:
    @dataclass
    class Queries:
        list_shows: Query_ListShows
        get_show: Query_GetShow

    @dataclass
    class UseCases:
        search_release: UseCase_SearchReleases
        grab_release: UseCase_GrabRelease
        update_release_file_matchings: UseCase_UpdateReleaseFileMatching
        sync_missing_series: UseCase_SyncMissingSeries
        import_releases_torrent_stats: UseCase_ImportReleasesTorrentStats
        export_finished_series: UseCase_ExportFinishedSeries
        re_grab_outdated_releases: UseCase_ReGrabOutdatedReleases
        delete_release: UseCase_DeleteRelease

    @dataclass
    class Repositories:
        shows: I_ShowsRepository
        releases: I_ReleasesRepository

    @dataclass
    class Services:
        release_searcher: I_ReleaseSearcher
        torrent_client: I_TorrentClient
        tvdb_client: I_TvdbClient
        series_service: I_SeriesService
        release_files_matching_autocompleter: ReleaseFileMatchingsAutocompleter

    db_manager: I_DBManager
    queries: Queries
    use_cases: UseCases
    repositories: Repositories
    services: Services


def _init_dependencies() -> Dependencies:
    session_maker = get_async_sessionmaker(app_settings.DB_PATH)

    db_manager = DBManager(session_maker)
    repositories = Dependencies.Repositories(
        shows=ShowsRepository(),
        releases=ReleasesRepository(),
    )

    services = Dependencies.Services(
        release_searcher=ProwlarrApiClient(
            base_url=app_settings.PROWLARR_BASE_URL,
            api_token=app_settings.PROWLARR_API_TOKEN,
        ),
        torrent_client=QBittorrentApiClient(
            base_url=app_settings.QBITTORRENT_BASE_URL,
            username=app_settings.QBITTORRENT_USERNAME,
            password=app_settings.QBITTORRENT_PASSWORD,
        ),
        tvdb_client=TVDBApiClient(
            api_token=app_settings.TVDB_API_TOKEN,
        ),
        series_service=SeriesService(
            base_url=app_settings.SONARR_BASE_URL,
            api_token=app_settings.SONARR_API_TOKEN,
        ),
        release_files_matching_autocompleter=ReleaseFileMatchingsAutocompleter(),
    )

    queries = Dependencies.Queries(
        list_shows=Query_ListShows(
            db_manager=db_manager,
            logger=logger.bind(component="Query.ListShows"),
        ),
        get_show=Query_GetShow(
            db_manager=db_manager,
            logger=logger.bind(component="Query.GetShows"),
        ),
    )

    use_cases = Dependencies.UseCases(
        search_release=UseCase_SearchReleases(
            db_manager=db_manager,
            release_searcher=services.release_searcher,
            shows_repository=repositories.shows,
            logger=logger.bind(component="UseCase.SearchReleases"),
        ),
        grab_release=UseCase_GrabRelease(
            db_manager=db_manager,
            release_searcher=services.release_searcher,
            shows_repository=repositories.shows,
            torrent_client=services.torrent_client,
            releases_repository=repositories.releases,
            logger=logger.bind(component="UseCase.GrabRelease"),
        ),
        update_release_file_matchings=UseCase_UpdateReleaseFileMatching(
            db_manager=db_manager,
            releases_repository=repositories.releases,
            release_files_matching_autocompleter=services.release_files_matching_autocompleter,
            logger=logger.bind(component="UseCase.UpdateReleaseFileMatching"),
        ),
        sync_missing_series=UseCase_SyncMissingSeries(
            db_manager=db_manager,
            series_service=services.series_service,
            shows_repository=repositories.shows,
            tvdb_client=services.tvdb_client,
            logger=logger.bind(component="UseCase.SyncMissingSeries"),
        ),
        import_releases_torrent_stats=UseCase_ImportReleasesTorrentStats(
            db_manager=db_manager,
            torrent_client=services.torrent_client,
            releases_repository=repositories.releases,
            logger=logger.bind(component="UseCase.ImportReleasesTorrentStats"),
        ),
        export_finished_series=UseCase_ExportFinishedSeries(
            db_manager=db_manager,
            releases_repository=repositories.releases,
            series_service=services.series_service,
            logger=logger.bind(component="UseCase.ExportFinishedSeries"),
        ),
        re_grab_outdated_releases=UseCase_ReGrabOutdatedReleases(
            db_manager=db_manager,
            release_searcher=services.release_searcher,
            torrent_client=services.torrent_client,
            releases_repository=repositories.releases,
            release_files_matching_autocompleter=services.release_files_matching_autocompleter,
            logger=logger.bind(component="UseCase.ReGrabOutdatedReleases"),
        ),
        delete_release=UseCase_DeleteRelease(
            db_manager=db_manager,
            releases_repository=repositories.releases,
            logger=logger.bind(component="UseCase.DeleteRelease"),
        ),
    )

    return Dependencies(
        db_manager=db_manager,
        queries=queries,
        use_cases=use_cases,
        repositories=repositories,
        services=services,
    )


dependencies = _init_dependencies()
