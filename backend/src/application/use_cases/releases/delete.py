from __future__ import annotations

import loguru

from src.application.interfaces.db_manager import I_DBManager
from src.application.interfaces.releases_repository import I_ReleasesRepository


class UseCase_DeleteRelease:
    def __init__(
        self,
        db_manager: I_DBManager,
        releases_repository: I_ReleasesRepository,
        logger: loguru.Logger,
    ) -> None:
        self.db_manager = db_manager
        self.releases_repository = releases_repository
        self.logger = logger

    async def process(self, name: str):
        self.logger.info("Deleting release", name=name)
        with self.logger.catch(reraise=True):
            return await self._process(name)

    async def _process(self, name):
        async with self.db_manager.begin_session() as db_session:
            await self.releases_repository.delete(db_session, name)
