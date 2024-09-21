from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.application.models import Release, Show
from src.db import async_session
from src.infrastructure.api_clients.prowlarr import ProwlarrApiClient
from src.infrastructure.api_clients.sonarr import (
    SonarrApiClient,
)
from src.infrastructure.api_clients.tvdb import TVDBApiClient


class ShowService:
    def __init__(self) -> None:
        self.sonarr_api_client = SonarrApiClient()
        self.tvdb_api_client = TVDBApiClient()
        self.prowlarr_api_client = ProwlarrApiClient()

    async def get_missing(self) -> list[Show]:
        async with async_session() as session, session.begin():
            return await session.scalars(select(Show).where(Show.is_missing))

    async def get_all(self) -> list[Show]:
        async with async_session() as session, session.begin():
            return await session.scalars(select(Show))

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
