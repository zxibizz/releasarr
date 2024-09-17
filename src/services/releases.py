import json
from datetime import datetime

from sqlalchemy import insert, select, update

from src.db import async_session
from src.deps.prowlarr import ProwlarrApiClient
from src.deps.qbittorrent import QBittorrentApiClient
from src.models import Release, ReleaseFileMatching


class ReleasesService:
    def __init__(self):
        self.qbittorrent_client = QBittorrentApiClient()
        self.prowlarr_client = ProwlarrApiClient()

    async def grab(
        self, show_id: int, search: str, search_name: str, download_url: str
    ):
        await self.qbittorrent_client.log_in()
        meta, torrent = await self.prowlarr_client.get_torrent(download_url)
        await self.qbittorrent_client.add_torrent(torrent)
        torrent_data = await self.qbittorrent_client.torrent_properties(meta.info_hash)

        async with async_session() as session, session.begin():
            await session.execute(
                insert(Release).values(
                    {
                        Release.name: torrent_data["name"],
                        Release.updated_at: datetime.now(),
                        Release.search: search,
                        Release.search_name: search_name,
                        Release.show_id: show_id,
                        Release.qbittorrent_guid: meta.info_hash,
                        Release.qbittorrent_data: json.dumps(torrent_data),
                    }
                )
            )
            await session.execute(
                insert(ReleaseFileMatching).values(
                    [
                        {
                            ReleaseFileMatching.release_name: torrent_data["name"],
                            ReleaseFileMatching.show_id: show_id,
                            ReleaseFileMatching.file_name: file.name,
                        }
                        for file in meta.files
                    ]
                )
            )

    async def update_file_matching(
        self, release_name: str, new_file_matching: list[dict]
    ):
        async with async_session() as session, session.begin():
            for m in new_file_matching:
                await session.execute(
                    update(ReleaseFileMatching)
                    .values(
                        {
                            ReleaseFileMatching.season_number: m["season_number"],
                            ReleaseFileMatching.episode_number: m["episode_number"],
                        }
                    )
                    .where(
                        ReleaseFileMatching.release_name == release_name,
                        ReleaseFileMatching.file_name == m["file_name"],
                    )
                )

    async def get_shows_having_finished_releases(self):
        await self.qbittorrent_client.log_in()
        stats = await self.qbittorrent_client.get_stats()
        finished_torrents = [
            t.infohash_v1
            for t in stats.torrents.values()
            if t.seen_complete is not None
        ]

        async with async_session() as session, session.begin():
            return list(
                await session.scalars(
                    select(Release.show_id).where(
                        Release.qbittorrent_guid.in_(finished_torrents)
                    )
                )
            )
