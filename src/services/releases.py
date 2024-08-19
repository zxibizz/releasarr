import json
from datetime import datetime

from sqlalchemy import insert

from src.db import async_session
from src.deps.prowlarr import ProwlarrApiClient
from src.deps.qbittorrent import QBittorrentApiClient
from src.models import Release, ReleaseFileMatching


class ReleasesService:
    def __init__(self):
        self.qbittorrent_client = QBittorrentApiClient()
        self.prowlarr_client = ProwlarrApiClient()

    async def grab(self, show_id: int, search: str, download_url: str):
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
