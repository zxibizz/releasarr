import asyncio
import json
from datetime import datetime

from pydantic import computed_field
from sqlalchemy import types
from sqlmodel import Field, Relationship, SQLModel

from src.application.schemas import ReleaseData
from src.infrastructure.api_clients.sonarr import Series
from src.infrastructure.api_clients.tvdb import TvdbShowData


class Show(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    sonarr_id: int | None = Field(unique=True)
    sonarr_data_raw: str = Field(exclude=True)
    tvdb_data_raw: str = Field(exclude=True)
    is_missing: bool = Field(default=False, index=True)
    missing_seasons: list[int] = Field(default=None, sa_type=types.JSON)
    prowlarr_search: str | None
    prowlarr_data_raw: str | None = Field(exclude=True)

    releases: list["Release"] = Relationship(back_populates="show")

    @computed_field
    @property
    def sonarr_data(self) -> Series:
        return Series.model_validate_json(self.sonarr_data_raw)

    @computed_field
    @property
    def tvdb_data(self) -> TvdbShowData:
        return TvdbShowData.model_validate_json(self.tvdb_data_raw)

    @computed_field
    @property
    def prowlarr_data(self) -> list[ReleaseData]:
        if not self.prowlarr_data_raw:
            return []
        return [
            ReleaseData.model_validate_json(obj)
            for obj in json.loads(self.prowlarr_data_raw)
        ]


class Release(SQLModel, table=True):
    name: str = Field(primary_key=True)
    updated_at: datetime
    search: str
    prowlarr_guid: str = Field(default="", nullable=True)
    prowlarr_data_raw: str = Field(default="", nullable=True)
    show_id: int = Field(default=None, foreign_key="show.id")
    qbittorrent_guid: str
    qbittorrent_data: str
    torrent_is_finished: bool = Field(default=False)
    torrent_stats_raw: str = Field(default=None, nullable=True)
    last_imported_files_hash: str = Field(default=None, nullable=True)
    last_exported_torrent_guid: str = Field(default=None, nullable=True)
    export_failures_count: int = Field(default=0)

    show: Show = Relationship(back_populates="releases")
    file_matchings: list["ReleaseFileMatching"] = Relationship(back_populates="release")

    @property
    def prowlarr_data(self) -> ReleaseData:
        if not self.prowlarr_data_raw:
            return None
        return ReleaseData.model_validate_json(self.prowlarr_data_raw)


class ReleaseFileMatching(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    release_name: str = Field(default=None, foreign_key="release.name")
    file_name: str
    show_id: int
    season_number: int = Field(default=None, nullable=True)
    episode_number: int = Field(default=None, nullable=True)

    release: Release = Relationship(back_populates="file_matchings")


async def main():
    from db import get_async_engine

    async with get_async_engine().begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(main())
