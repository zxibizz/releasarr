import asyncio
import os

import httpx


class QBittorrentApiClient:
    def __init__(self) -> None:
        self.base_url = os.environ.get("QBITTORRENT_BASE_URL")
        self.client = httpx.AsyncClient(base_url=self.base_url)

    async def log_in(self):
        res = await self.client.post(
            "/auth/login",
            data={
                "username": os.environ.get("QBITTORRENT_USERNAME"),
                "password": os.environ.get("QBITTORRENT_PASSWORD"),
            },
        )
        res.raise_for_status()

    async def add_torrent(self, torrent: bytes):
        files = {
            "fileselect[]": (
                "torrent.torrent",
                torrent,
                "application/x-bittorrent",
            )
        }
        res = await self.client.post(
            "/torrents/add",
            data={
                "autoTMM": False,
                "savepath": "/Media/Downloads",
                "rename": None,
                "category": None,
                "paused": False,
                "stopCondition": None,
                "contentLayout": "Original",
                "dlLimit": "NaN",
                "upLimit": "NaN",
            },
            files=files,
        )
        res.raise_for_status()

    async def torrent_properties(self, hash):
        res = await self.client.get("/torrents/properties", params={"hash": hash})
        res_data = res.json()
        res_data = {
            "addition_date": 1719045144,
            "comment": "http://animelayer.ru/torrent/66128cf65dccfa21bf68bea2/",
            "completion_date": -1,
            "created_by": "andromeda88",
            "creation_date": 1718805137,
            "dl_limit": -1,
            "dl_speed": 0,
            "dl_speed_avg": 0,
            "download_path": "/Media/Torrents",
            "eta": 8640000,
            "hash": "18dee27591b17cb1edd016f3dd13c10592fd9e7d",
            "infohash_v1": "18dee27591b17cb1edd016f3dd13c10592fd9e7d",
            "infohash_v2": "",
            "is_private": False,
            "last_seen": -1,
            "name": "Yoru no Kurage wa Oyogenai",
            "nb_connections": 0,
            "nb_connections_limit": 100,
            "peers": 0,
            "peers_total": 0,
            "piece_size": 2097152,
            "pieces_have": 0,
            "pieces_num": 1603,
            "reannounce": 0,
            "save_path": "/Media/Downloads",
            "seeding_time": 0,
            "seeds": 0,
            "seeds_total": 0,
            "share_ratio": 0,
            "time_elapsed": 0,
            "total_downloaded": 0,
            "total_downloaded_session": 0,
            "total_size": 3360560303,
            "total_uploaded": 0,
            "total_uploaded_session": 0,
            "total_wasted": 0,
            "up_limit": -1,
            "up_speed": 0,
            "up_speed_avg": 0,
        }


if __name__ == "__main__":
    import django

    django.setup()

    from admin.app.models import SonarrReleaseSelect
    from bot.config import get_dependecies, init_dependencies
    from bot.dependencies.prowlarr import ProwlarrApiClient

    init_dependencies()

    dependencies = get_dependecies()
    prowlarr_api_client: ProwlarrApiClient = dependencies.prowlarr_api_client

    client = QBittorrentApiClient()

    async def _main():
        select = await SonarrReleaseSelect.objects.aget(id=34)
        prowlarr_torrent = await prowlarr_api_client.get_torrent(
            select.prowlarr_results[0].download_url
        )
        await client.add_torrent(prowlarr_torrent.content)
        status = await client.torrent_properties(prowlarr_torrent.info_hash)
        print(status)

    asyncio.run(_main())
