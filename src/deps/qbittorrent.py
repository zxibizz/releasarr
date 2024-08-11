import asyncio
import os
from datetime import datetime
from typing import Optional

import httpx
from pydantic import BaseModel


class QBittorrentStats(BaseModel):
    torrents: dict[str, "QBittorrentTorrentStats"]


class QBittorrentTorrentStats(BaseModel):
    added_on: datetime
    amount_left: int
    auto_tmm: bool
    availability: float
    category: str
    completed: int
    completion_on: datetime
    content_path: str
    dl_limit: int
    dlspeed: int
    download_path: str
    downloaded: int
    downloaded_session: int
    eta: int
    f_l_piece_prio: bool
    force_start: bool
    inactive_seeding_time_limit: int
    infohash_v1: str
    infohash_v2: Optional[str]
    last_activity: datetime
    magnet_uri: str
    max_inactive_seeding_time: int
    max_ratio: int
    max_seeding_time: int
    name: str
    num_complete: int
    num_incomplete: int
    num_leechs: int
    num_seeds: int
    priority: int
    progress: float
    ratio: float
    ratio_limit: int
    save_path: str
    seeding_time: int
    seeding_time_limit: int
    seen_complete: datetime
    seq_dl: bool
    size: int
    state: str
    super_seeding: bool
    tags: str
    time_active: int
    total_size: int
    tracker: str
    trackers_count: int
    up_limit: int
    uploaded: int
    uploaded_session: int
    upspeed: int

    class Config:
        json_encoders = {datetime: lambda v: int(v.timestamp())}


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
        return res.json()
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

    async def get_stats(self):
        res = await self.client.get("/sync/maindata")
        res.raise_for_status()
        return QBittorrentStats.model_validate_json(res.content)


if __name__ == "__main__":
    client = QBittorrentApiClient()

    async def _main():
        await client.log_in()
        stats = await client.get_stats()
        print(stats)

    asyncio.run(_main())
