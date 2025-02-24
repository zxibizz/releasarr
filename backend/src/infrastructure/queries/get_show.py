from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.application.models import Release, Show
from src.db import async_session


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
    torrent_stats_raw: str
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
    async def execute(self, show_id: int) -> GetShowQueryResponse | None:
        async with async_session.begin() as session:
            q = (
                select(Show)
                .where(Show.id == show_id)
                .options(
                    joinedload(Show.releases).options(
                        joinedload(Release.file_matchings)
                    ),
                )
            )
            res = await session.scalar(q)
            if res is None:
                return
            return GetShowQueryResponse.model_validate(obj=res)
