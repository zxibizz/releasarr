from sqlalchemy import select

from src.application.models import Show
from src.db import async_session


class Query_ListShows:
    async def execute(self, only_missing: bool) -> list[Show]:
        async with async_session() as session, session.begin():
            q = select(Show)

            if only_missing:
                q = q.where(Show.is_missing)

            return await session.scalars(q)
