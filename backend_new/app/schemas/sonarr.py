from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class MissingSeries(BaseModel):
    id: int
    tvdb_id: int
    season_numbers: list[int]


class Episode(BaseModel):
    id: int
    episode_number: int


class Season(BaseModel):
    season_number: int
    episode_file_count: int
    episode_count: int
    episodes: list[Episode]
    total_episodes_count: int
    previous_airing: datetime | None = None


class Series(BaseModel):
    id: int
    path: str
    tvdb_id: int
    seasons: list[Season]


class SeriesImportFile(BaseModel):
    episode_ids: list[int]
    folder_name: str
    indexer_flags: int = 0
    path: str
    release_type: str = "singleEpisode"
    series_id: int


class ManualImportResult(BaseModel):
    successfully_imported: bool = True
