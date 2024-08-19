import json

from sqlalchemy import select, update
from sqlalchemy.orm import joinedload

from src.db import async_session
from src.deps.prowlarr import ProwlarrApiClient
from src.deps.sonarr import SonarrApiClient, SonarrSeries
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
