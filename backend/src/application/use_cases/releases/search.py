from __future__ import annotations

import loguru

from src.application.interfaces.db_manager import I_DBManager
from src.application.interfaces.release_searcher import I_ReleaseSearcher
from src.application.interfaces.shows_repository import I_ShowsRepository


class UseCase_SearchReleases:
    def __init__(
        self,
        db_manager: I_DBManager,
        release_searcher: I_ReleaseSearcher,
        shows_repository: I_ShowsRepository,
        logger: loguru.Logger,
    ) -> None:
        self.release_searcher = release_searcher
        self.db_manager = db_manager
        self.shows_repository = shows_repository
        self.logger = logger

    async def process(self, show_id: int, search_string: str):
        self.logger.info(
            "Searching releases",
            show_id=show_id,
            search_string=search_string,
        )
        with self.logger.catch(reraise=True):
            return await self._process(show_id=show_id, search_string=search_string)

    async def _process(self, show_id: int, search_string: str):
        releases = await self.release_searcher.search(search_string)
        async with self.db_manager.begin_session() as db_session:
            await self.shows_repository.save_releases_seach_results(
                db_session=db_session,
                show_id=show_id,
                search_string=search_string,
                releases_search_result=releases,
            )
