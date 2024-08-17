import asyncio
from datetime import datetime

from sqlalchemy import types
from sqlmodel import Field, SQLModel

from src.db import async_engine
from src.deps.sonarr import SonarrSeries
from src.deps.tvdb import TvdbShowData


class Show(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    sonarr_id: int | None = Field(unique=True)
    sonarr_data_raw: str
    tvdb_data_raw: str
    is_missing: bool = Field(default=False, index=True)
    missing_seasons: list[int] = Field(default=None, sa_type=types.JSON)
    prowlarr_search: str | None
    prowlarr_data_raw: str | None

    @property
    def sonarr_data(self):
        return SonarrSeries.model_validate_json(self.sonarr_data_raw)

    @property
    def tvdb_data(self):
        return TvdbShowData.model_validate_json(self.tvdb_data_raw)


class Release(SQLModel, table=True):
    name: str = Field(primary_key=True)
    updated_at: datetime
    search: str
    show_id: int
    qbittorrent_guid: str
    qbittorrent_data: str


class ReleaseFileMatching(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    show_id: int
    file_name: str
    season_number: int
    episode_number: int


async def main():
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(main())
