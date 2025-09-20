from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class EpisodeMapping(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    season: int
    episode: int
    title: str | None = None


class FileRequestMapping(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    request_id: int
    request_title: str
    mapping_type: Literal["episode", "movie", "season"]
    season: int | None = None
    episode: int | None = None


class ReleaseFile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    path: str
    size: int
    episode_mapping: EpisodeMapping | None = None
    request_mapping: FileRequestMapping | None = None


class Release(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    hash: str | None = None
    size: int
    files: list[ReleaseFile]
    status: Literal["pending", "downloading", "seeding", "completed", "failed"]
    progress: float
    download_speed: int
    upload_speed: int
    seeders: int
    leechers: int
    ratio: float
    added_date: datetime
    completed_date: datetime | None = None
    request_ids: list[int]
    torrent_source: str | None = None
    quality: str | None = None


class ReleaseStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_releases: int
    active_downloads: int
    completed_releases: int
    total_size: int
    total_uploaded: int
    total_downloaded: int
