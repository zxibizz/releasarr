import json

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.shows_repository import I_ShowsRepository
from src.application.models import Show
from src.application.schemas import ReleaseData


class ShowsRepository(I_ShowsRepository):
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
