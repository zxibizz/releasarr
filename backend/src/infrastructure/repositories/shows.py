import json

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.application.interfaces.shows_repository import I_ShowsRepository
from src.application.models import Release, Show
from src.application.schemas import ReleaseData


class ShowsRepository(I_ShowsRepository):
    async def get_show_with_releases(
        self, db_session: AsyncSession, show_id: int
    ) -> Show | None:
        return await db_session.scalar(
            select(Show)
            .where(Show.id == show_id)
            .options(
                joinedload(Show.releases).options(joinedload(Release.file_matchings)),
            )
        )

    async def get_series(self, db_session: AsyncSession, series_id: int) -> Show | None:
        return await db_session.scalar(select(Show).where(Show.sonarr_id == series_id))

    async def save_releases_seach_results(
        self,
        db_session: AsyncSession,
        show_id: int,
        search_string: str,
        releases_search_result: list[ReleaseData],
    ):
        await db_session.execute(
            update(Show)
            .values(
                {
                    Show.prowlarr_search: search_string,
                    Show.prowlarr_data_raw: json.dumps(
                        [
                            release.model_dump_json()
                            for release in releases_search_result
                        ]
                    ),
                }
            )
            .where(Show.id == show_id)
        )

    async def unflag_all_missing_series(self, db_session: AsyncSession) -> None:
        await db_session.execute(
            update(Show)
            .values(
                {
                    Show.is_missing: False,
                    Show.missing_seasons: None,
                }
            )
            .where(Show.sonarr_id.is_not(None))
        )

    async def save(self, db_session: AsyncSession, show: Show) -> None:
        db_session.add(show)
