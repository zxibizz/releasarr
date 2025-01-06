import json
from datetime import datetime

from src.application.interfaces.db_manager import I_DBManager
from src.application.interfaces.release_searcher import I_ReleaseSearcher
from src.application.interfaces.releases_repository import I_ReleasesRepository
from src.application.interfaces.shows_repository import I_ShowsRepository
from src.application.interfaces.torrent_client import I_TorrentClient
from src.application.models import Release, ReleaseFileMatching, Show
from src.application.schemas import ReleaseData


class UseCase_GrabRelease:
    def __init__(
        self,
        db_manager: I_DBManager,
        release_searcher: I_ReleaseSearcher,
        shows_repository: I_ShowsRepository,
        torrent_client: I_TorrentClient,
        releases_repository: I_ReleasesRepository,
    ) -> None:
        self.db_manager = db_manager
        self.release_searcher = release_searcher
        self.shows_repository = shows_repository
        self.torrent_client = torrent_client
        self.releases_repository = releases_repository

    async def process(self, show_id: int, release_pk: str) -> None:
        async with self.db_manager.begin_session() as db_session:
            show: Show = await self.shows_repository.get_show_with_releases(
                db_session=db_session, show_id=show_id
            )
            release_data: ReleaseData = [
                pd for pd in show.prowlarr_data if pd.pk == release_pk
            ][0]

            meta, raw_torrent = await self.release_searcher.get_torrent(
                release_data.download_url
            )
            await self.torrent_client.add_torrent(raw_torrent)
            torrent_data = await self.torrent_client.torrent_properties(meta.info_hash)

            release = Release(
                name=torrent_data["name"],
                updated_at=datetime.now(),
                search=show.prowlarr_search,
                prowlarr_data_raw=release_data.model_dump_json(),
                show_id=show_id,
                qbittorrent_guid=meta.info_hash,
                qbittorrent_data=json.dumps(torrent_data),
                file_matchings=[
                    ReleaseFileMatching(
                        release_name=torrent_data["name"],
                        show_id=show_id,
                        file_name=file.name,
                    )
                    for file in meta.files
                ],
            )
            await self.releases_repository.create(
                db_session=db_session, release=release
            )
