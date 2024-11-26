import os
from datetime import datetime
from typing import Optional

import httpx
from pydantic import BaseModel, Field


class QBittorrentStats(BaseModel):
    torrents: dict[str, "QBittorrentTorrentStats"] = Field(default_factory=lambda: {})


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
        self._login_happened = False

    async def log_in(self):
        if self._login_happened:
            return
        res = await self.client.post(
            "/auth/login",
            data={
                "username": os.environ.get("QBITTORRENT_USERNAME"),
                "password": os.environ.get("QBITTORRENT_PASSWORD"),
            },
        )
        res.raise_for_status()
        self._login_happened = True

    async def add_torrent(self, torrent: bytes):
        if not self._login_happened:
            await self.log_in()

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
        if not self._login_happened:
            await self.log_in()

        res = await self.client.get("/torrents/properties", params={"hash": hash})
        return res.json()

    async def get_stats(self):
        if not self._login_happened:
            await self.log_in()

        res = await self.client.get("/sync/maindata")
        res.raise_for_status()
        return QBittorrentStats.model_validate_json(res.content)
