from __future__ import annotations

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.factory import get_clients
from app.db.session import AsyncSessionLocal
from app.models import Show
from app.schemas.sonarr import MissingSeries, Series


class MissingSeriesSyncService:
    def __init__(self) -> None:
        self.clients = get_clients()
        self._session_factory = AsyncSessionLocal

    async def run(self) -> None:
        sonarr = self.clients.sonarr
        tvdb = self.clients.tvdb
        if not sonarr.enabled:
            logger.info("Skipping missing series sync; Sonarr disabled")
            return

        missing_series = await sonarr.get_missing()
        if not missing_series:
            logger.info("No missing series reported by Sonarr")
            async with self._session_factory() as session:
                await session.execute(
                    update(Show).values(is_missing=False, missing_seasons=None)
                )
                await session.commit()
            return

        async with self._session_factory() as session:
            await session.execute(
                update(Show).values(is_missing=False, missing_seasons=None)
            )
            for missing in missing_series:
                await self._upsert_show(session, missing, sonarr, tvdb)
            await session.commit()

    async def _upsert_show(
        self,
        session: AsyncSession,
        missing: MissingSeries,
        sonarr_client,
        tvdb_client,
    ) -> None:
        show = await session.scalar(select(Show).where(Show.sonarr_id == missing.id))
        sonarr_series: Series | None = None
        tvdb_data = None
        try:
            sonarr_series = await sonarr_client.get_series(missing.id)
        except Exception as exc:  # pragma: no cover - logging only
            logger.warning("Failed to fetch Sonarr series %s: %s", missing.id, exc)

        if tvdb_client.enabled and missing.tvdb_id:
            try:
                tvdb_data = await tvdb_client.get_series(missing.tvdb_id)
            except Exception as exc:  # pragma: no cover - logging only
                logger.exception("Failed to fetch TVDB series", missing.tvdb_id, exc)

        if show is None:
            show = Show(sonarr_id=missing.id)
            session.add(show)

        show.tvdb_id = missing.tvdb_id
        show.is_missing = True
        show.missing_seasons = sorted(missing.season_numbers)

        if sonarr_series:
            show.sonarr_data = sonarr_series.model_dump(mode="json")
            if not show.prowlarr_search:
                show.prowlarr_search = (
                    sonarr_series.path or sonarr_series.id and str(sonarr_series.id)
                )
        if tvdb_data:
            show.tvdb_data = tvdb_data.model_dump(mode="json")
            if not show.prowlarr_search:
                show.prowlarr_search = tvdb_data.title
        if tvdb_data:
            show.prowlarr_data = show.prowlarr_data or {}


async def sync_missing_series_once() -> None:
    await MissingSeriesSyncService().run()
