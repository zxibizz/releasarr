from __future__ import annotations

from datetime import datetime

import loguru
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.application.interfaces.db_manager import I_DBManager
from src.application.models import Release, Show


class DTO_Show_SonarrSeriesData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    path: str
    tvdb_id: int
    seasons: list["DTO_Show_SonarrSeason"]


class DTO_Show_SonarrSeason(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    season_number: int
    episode_file_count: int
    episode_count: int
    episodes: list["DTO_Show_SonarrEpisode"]
    total_episodes_count: int
    previous_airing: datetime | None


class DTO_Show_SonarrEpisode(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    episode_number: int | None


class DTO_Show_ProwlarrData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    guid: str
    age: int
    grabs: int
    info_url: str
    size: int
    title: str
    indexer: str
    indexer_id: int
    seeders: int
    leechers: int
    download_url: str
    pk: str


class DTO_Show_TvdbShowData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    year: int
    genres: list
    country: str
    title: str
    title_en: str | None
    image_url: str | None
    overview: str


class DTO_Show_Release(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    updated_at: datetime
    search: str
    prowlarr_guid: str
    prowlarr_data_raw: str
    show_id: int
    qbittorrent_guid: str
    qbittorrent_data: str
    torrent_is_finished: bool
    last_imported_files_hash: str | None
    last_exported_torrent_guid: str | None
    export_failures_count: int

    file_matchings: list["DTO_Show_ReleaseFileMatching"]


class DTO_Show_ReleaseFileMatching(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    release_name: str
    file_name: str
    show_id: int
    season_number: int | None
    episode_number: int | None


class DTO_Show(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sonarr_data: str
    tvdb_data_raw: str
    is_missing: bool
    missing_seasons: list[int] | None
    prowlarr_search: str | None
    prowlarr_data: str | None

    tvdb_data: DTO_Show_TvdbShowData
    sonarr_data: DTO_Show_SonarrSeriesData
    releases: list[DTO_Show_Release]
    prowlarr_data: list[DTO_Show_ProwlarrData]


class Query_GetShow:
    def __init__(
        self,
        db_manager: I_DBManager,
        logger: loguru.Logger,
    ) -> None:
        self.db_manager = db_manager
        self.logger = logger

    async def execute(self, show_id: int) -> DTO_Show | None:
        self.logger.info(
            "Get show",
            show_id=show_id,
        )
        with self.logger.catch(reraise=True):
            async with self.db_manager.begin_session() as db_session:
                return await self._execute(db_session, show_id)

    async def _execute(self, db_session: AsyncSession, show_id: int) -> DTO_Show | None:
        q = (
            select(Show)
            .where(Show.id == show_id)
            .options(
                joinedload(Show.releases).options(joinedload(Release.file_matchings)),
            )
        )
        res = await db_session.scalar(q)
        if res is None:
            return
        return DTO_Show.model_validate(obj=res)
