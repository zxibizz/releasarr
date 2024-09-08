import asyncio
import json
from datetime import datetime

from sqlalchemy import types
from sqlmodel import Field, Relationship, SQLModel

from src.db import async_engine
from src.deps.prowlarr import ProwlarrRelease
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

    releases: list["Release"] = Relationship(back_populates="show")

    @property
    def sonarr_data(self) -> SonarrSeries:
        return SonarrSeries.model_validate_json(self.sonarr_data_raw)

    @property
    def tvdb_data(self) -> TvdbShowData:
        return TvdbShowData.model_validate_json(self.tvdb_data_raw)

    @property
    def prowlarr_data(self) -> list[ProwlarrRelease]:
        if not self.prowlarr_data_raw:
            return []
        return [
            ProwlarrRelease.model_validate_json(obj)
            for obj in json.loads(self.prowlarr_data_raw)
        ]


class Release(SQLModel, table=True):
    name: str = Field(primary_key=True)
    updated_at: datetime
    search: str
    prowlarr_guid: str = Field(default="", nullable=True)
    show_id: int = Field(default=None, foreign_key="show.id")
    qbittorrent_guid: str
    qbittorrent_data: str
    last_imported_files_hash: str = Field(default=None, nullable=True)

    show: Show = Relationship(back_populates="releases")
    file_matchings: list["ReleaseFileMatching"] = Relationship(back_populates="release")


class ReleaseFileMatching(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    release_name: str = Field(default=None, foreign_key="release.name")
    file_name: str
    show_id: int
    season_number: int | None
    episode_number: int | None

    release: Release = Relationship(back_populates="file_matchings")


async def main():
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(main())
