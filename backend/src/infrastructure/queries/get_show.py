from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.application.models import Release, Show
from src.db import async_session


class Query_GetShow:
    async def execute(self, show_id: int) -> Show | None:
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
            return await session.scalar(q)
