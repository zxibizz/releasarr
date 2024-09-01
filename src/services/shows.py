import json
import os

from sqlalchemy import select, update
from sqlalchemy.orm import joinedload

from src.db import async_session
from src.deps.prowlarr import ProwlarrApiClient
from src.deps.sonarr import SonarrApiClient, SonarrImportFile, SonarrSeries
from src.deps.tvdb import TVDBApiClient, TvdbShowData
from src.models import Release, Show


class ShowService:
    def __init__(self) -> None:
        self.sonarr_api_client = SonarrApiClient()
        self.tvdb_api_client = TVDBApiClient()
        self.prowlarr_api_client = ProwlarrApiClient()

    async def get_missing(self) -> list[Show]:
        async with async_session() as session, session.begin():
            return await session.scalars(select(Show).where(Show.is_missing))

    async def get_show(self, show_id: int) -> Show:
        async with async_session() as session, session.begin():
            return await session.scalar(
                select(Show)
                .where(Show.id == show_id)
                .options(
                    joinedload(Show.releases).options(
                        joinedload(Release.file_matchings)
                    ),
                )
            )

    async def search_show_releases(self, show_id: int, search: str):
        async with async_session() as session, session.begin():
            releases = await self.prowlarr_api_client.search(search)
            await session.execute(
                update(Show)
                .values(
                    {
                        Show.prowlarr_search: search,
                        Show.prowlarr_data_raw: json.dumps(
                            [release.model_dump_json() for release in releases]
                        ),
                    }
                )
                .where(Show.id == show_id)
            )

    async def sync_missing(self):
        missing_series = await self.sonarr_api_client.get_missing()
        async with async_session() as session, session.begin():
            await session.execute(
                update(Show).values(
                    {
                        Show.is_missing: False,
                        Show.missing_seasons: None,
                    }
                )
            )
            for m in missing_series:
                show = await session.scalar(select(Show).where(Show.sonarr_id == m.id))
                if not show:
                    tvdb_data: TvdbShowData = await self.tvdb_api_client.get_series(
                        m.tvdb_id
                    )
                    sonarr_data: SonarrSeries = await self.sonarr_api_client.get_series(
                        m.id
                    )
                    show = Show(
                        sonarr_id=m.id,
                        tvdb_data_raw=tvdb_data.model_dump_json(),
                        sonarr_data_raw=sonarr_data.model_dump_json(),
                    )

                show.is_missing = True
                show.missing_seasons = m.season_numbers
                show.prowlarr_search = None
                show.prowlarr_data_raw = None
                session.add(show)

            await session.commit()

    async def sync_show_release_files(self, show_id: int):
        async with async_session() as session, session.begin():
            show = await self.get_show(show_id)
            for release in show.releases:
                import_files = []
                for file_matching in release.file_matchings:
                    torrent_data = json.loads(release.qbittorrent_data)
                    episode_id = None
                    for season in show.sonarr_data.seasons:
                        if season.season_number != file_matching.season_number:
                            continue
                        for episode in season.episodes:
                            if episode.episode_number == file_matching.episode_number:
                                episode_id = episode.id
                    if episode_id is not None:
                        import_files.append(
                            SonarrImportFile(
                                episode_ids=[episode_id],
                                folder_name=torrent_data["name"],
                                path=os.path.join(
                                    torrent_data["save_path"],
                                    file_matching.file_name,
                                ),
                                series_id=show.sonarr_id,
                            )
                        )
                if import_files:
                    await self.sonarr_api_client.manual_import(import_files)
