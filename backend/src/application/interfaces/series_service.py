from datetime import datetime
from typing import Protocol

from pydantic import BaseModel


class MissingSeries(BaseModel):
    id: int
    tvdb_id: int
    season_numbers: list[int]


class Series(BaseModel):
    id: int
    path: str
    tvdb_id: int
    seasons: list["Season"]


class Season(BaseModel):
    season_number: int
    episode_file_count: int
    episode_count: int
    episodes: list["Episode"]
    total_episodes_count: int
    previous_airing: datetime | None


class Episode(BaseModel):
    id: int
    episode_number: int


class SeriesImportFile(BaseModel):
    episode_ids: list[int]
    folder_name: str
    indexer_flags: int = 0
    # languages
    path: str
    # quantity
    release_type: str = "singleEpisode"
    series_id: int


class E_SeriesManualImportError(Exception): ...


class I_SeriesService(Protocol):
    async def get_missing(self) -> list[MissingSeries]: ...

    async def get_series(self, series_id) -> Series: ...

    async def manual_import(self, import_files: list[SeriesImportFile]) -> None: ...
