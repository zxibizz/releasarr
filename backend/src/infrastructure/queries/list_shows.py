from __future__ import annotations

import loguru
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.db_manager import I_DBManager
from src.application.models import Show


class Query_ListShows:
    def __init__(
        self,
        db_manager: I_DBManager,
        logger: loguru.Logger,
    ) -> None:
        self.db_manager = db_manager
        self.logger = logger

    async def execute(self, only_missing: bool) -> list[Show]:
        self.logger.info(
            "List shows",
            only_missing=only_missing,
        )
        with self.logger.catch(reraise=True):
            async with self.db_manager.begin_session() as db_session:
                return await self._execute(db_session, only_missing)

    async def _execute(
        self, db_session: AsyncSession, only_missing: bool
    ) -> list[Show]:
        q = select(Show)

        if only_missing:
            q = q.where(Show.is_missing)

        return await db_session.scalars(q)
