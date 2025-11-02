from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TorrentStats(BaseModel):
    added_on: datetime
    amount_left: int
    auto_tmm: bool
    availability: float
    category: str | None = None
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
    infohash_v2: str | None = None
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
    tracker: str | None = None
    trackers_count: int
    up_limit: int
    uploaded: int
    uploaded_session: int
    upspeed: int


class Stats(BaseModel):
    torrents: dict[str, TorrentStats] = Field(default_factory=dict)
