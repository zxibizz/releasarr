from dataclasses import dataclass

from src.application.interfaces.db_manager import I_DBManager
from src.application.interfaces.release_searcher import I_ReleaseSearcher
from src.application.interfaces.releases_repository import I_ReleasesRepository
from src.application.interfaces.shows_repository import I_ShowsRepository
from src.application.interfaces.torrent_client import I_TorrentClient
from src.application.use_cases.releases.grab import UseCase_GrabRelease
from src.application.use_cases.releases.search import UseCase__SearchReleases
from src.infrastructure.api_clients.prowlarr import ProwlarrApiClient
from src.infrastructure.api_clients.qbittorrent import QBittorrentApiClient
from src.infrastructure.db_manager import DBManager
from src.infrastructure.repositories.releases import ReleasesRepository
from src.infrastructure.repositories.shows import ShowsRepository


@dataclass
class Dependencies:
    @dataclass
    class UseCases:
        search_release: UseCase__SearchReleases
        grab_release: UseCase_GrabRelease

    @dataclass
    class Repositories:
        shows: I_ShowsRepository
        releases: I_ReleasesRepository

    @dataclass
    class Services:
        release_searcher: I_ReleaseSearcher
        torrent_client: I_TorrentClient

    db_manager: I_DBManager
    use_cases: UseCases
    repositories: Repositories
    services: Services


def init_dependencies() -> Dependencies:
    db_manager = DBManager()
    repositories = Dependencies.Repositories(
        shows=ShowsRepository(),
        releases=ReleasesRepository(),
    )

    services = Dependencies.Services(
        release_searcher=ProwlarrApiClient(),
        torrent_client=QBittorrentApiClient(),
    )

    use_cases = Dependencies.UseCases(
        search_release=UseCase__SearchReleases(
            db_manager=db_manager,
            release_searcher=services.release_searcher,
            shows_repository=repositories.shows,
        ),
        grab_release=UseCase_GrabRelease(
            db_manager=db_manager,
            release_searcher=services.release_searcher,
            shows_repository=repositories.shows,
            torrent_client=services.torrent_client,
            releases_repository=repositories.releases,
        ),
    )

    return Dependencies(
        db_manager=db_manager,
        use_cases=use_cases,
        repositories=repositories,
        services=services,
    )


dependencies = init_dependencies()
