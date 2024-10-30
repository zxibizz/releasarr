from dataclasses import dataclass

from src.application.interfaces.db_manager import I_DBManager
from src.application.interfaces.release_searcher import I_ReleaseSearcher
from src.application.interfaces.shows_repository import I_ShowsRepository
from src.application.use_cases.releases.search import UseCase__SearchReleases
from src.infrastructure.api_clients.prowlarr import ProwlarrApiClient
from src.infrastructure.db_manager import DBManager
from src.infrastructure.repositories.shows import ShowsRepository


@dataclass
class Dependencies:
    @dataclass
    class UseCases:
        search_release: UseCase__SearchReleases

    @dataclass
    class Repositories:
        shows: I_ShowsRepository

    @dataclass
    class Services:
        release_searcher: I_ReleaseSearcher

    db_manager: I_DBManager
    use_cases: UseCases
    repositories: Repositories
    services: Services


def init_dependencies() -> Dependencies:
    db_manager = DBManager()
    repositories = Dependencies.Repositories(shows=ShowsRepository())

    services = Dependencies.Services(
        release_searcher=ProwlarrApiClient(),
    )

    use_cases = Dependencies.UseCases(
        search_release=UseCase__SearchReleases(
            db_manager=db_manager,
            release_searcher=services.release_searcher,
            shows_repository=repositories.shows,
        )
    )

    return Dependencies(
        db_manager=db_manager,
        use_cases=use_cases,
        repositories=repositories,
        services=services,
    )


dependencies = init_dependencies()
