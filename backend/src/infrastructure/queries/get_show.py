from __future__ import annotations

from datetime import datetime

import loguru
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.application.interfaces.db_manager import I_DBManager
from src.application.models import Release, Show


class GetShowQueryResponse__SonarrSeriesData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    path: str
    tvdb_id: int
    seasons: list["GetShowQueryResponse__SonarrSeason"]


class GetShowQueryResponse__SonarrSeason(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    season_number: int
    episode_file_count: int
    episode_count: int
    episodes: list["GetShowQueryResponse__SonarrEpisode"]
    total_episodes_count: int
    previous_airing: datetime | None


class GetShowQueryResponse__SonarrEpisode(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    episode_number: int | None


class GetShowQueryResponse__ProwlarrData(BaseModel):
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


class GetShowQueryResponse__TvdbShowData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    year: int
    genres: list
    country: str
    title: str
    title_en: str | None
    image_url: str | None
    overview: str


class GetShowQueryResponse__Release(BaseModel):
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

    file_matchings: list["GetShowQueryResponse__ReleaseFileMatching"]


class GetShowQueryResponse__ReleaseFileMatching(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    release_name: str
    file_name: str
    show_id: int
    season_number: int | None
    episode_number: int | None


class GetShowQueryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sonarr_data: str
    tvdb_data_raw: str
    is_missing: bool
    missing_seasons: list[int]
    prowlarr_search: str | None
    prowlarr_data: str | None

    tvdb_data: GetShowQueryResponse__TvdbShowData
    sonarr_data: GetShowQueryResponse__SonarrSeriesData
    releases: list[GetShowQueryResponse__Release]
    prowlarr_data: list[GetShowQueryResponse__ProwlarrData]


class Query_GetShow:
    def __init__(
        self,
        db_manager: I_DBManager,
        logger: loguru.Logger,
    ) -> None:
        self.db_manager = db_manager
        self.logger = logger

    async def execute(self, show_id: int) -> list[Show]:
        self.logger.info(
            "Get show",
            show_id=show_id,
        )
        with self.logger.catch(reraise=True):
            async with self.db_manager.begin_session() as db_session:
                return await self._execute(db_session, show_id)

    async def _execute(
        self, db_session: AsyncSession, show_id: int
    ) -> GetShowQueryResponse | None:
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
        return GetShowQueryResponse.model_validate(obj=res)
