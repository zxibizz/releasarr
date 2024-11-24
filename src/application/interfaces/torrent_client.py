from datetime import datetime
from typing import Optional, Protocol

from pydantic import BaseModel


class Stats(BaseModel):
    torrents: dict[str, "TorrentStats"]


class TorrentStats(BaseModel):
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


class I_TorrentClient(Protocol):
    async def add_torrent(self, raw_torrent: bytes) -> None: ...

    async def torrent_properties(self, hash: str) -> dict: ...

    async def get_stats(self) -> Stats: ...
