from sqlalchemy import select

from src.application.models import Show
from src.db import async_session


class Query_GetShow:
    async def execute(self, show_id: int) -> Show | None:
        async with async_session.begin() as session:
            q = select(Show).where(Show.id == show_id)
            return await session.scalar(q)
