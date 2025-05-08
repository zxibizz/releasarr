import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.sonarr.client import MissingSeries, SonarrApiClient
from app.sonarr.models import SonarrRequest
from app.sonarr.schemas import SonarrEpisode


class SyncMissingSeries:
    def __init__(
        self,
        db_session: AsyncSession,
        sonarr_client: SonarrApiClient,
        logger: logging.Logger,
    ) -> None:
        self.db_session = db_session
        self.sonarr_client = sonarr_client
        self.logger = logger

    async def process(self) -> None:
        self.logger.info("Syncing missing series")
        try:
            await self._process()
        except Exception as e:
            self.logger.error(f"Error syncing missing series: {str(e)}")
            raise

    async def _process(self) -> None:
        # Get missing series from Sonarr
        missing_series_list = await self.sonarr_client.get_missing()

        # Reset missing flag on all existing requests
        await self._reset_missing_flag()

        # Process each missing series
        for missing_series in missing_series_list:
            await self._process_missing_series(missing_series)

    async def _reset_missing_flag(self) -> None:
        # Find all SonarrRequest objects with is_missing=True
        stmt = select(SonarrRequest).where(SonarrRequest.is_missing.is_(True))
        result = await self.db_session.execute(stmt)
        requests = result.scalars().all()

        # Update them to is_missing=False
        for request in requests:
            request.is_missing = False

        await self.db_session.commit()

    async def _process_missing_series(self, missing_series: MissingSeries) -> None:
        # Get detailed series information from Sonarr
        series_data = await self.sonarr_client.get_series(missing_series.id)

        # Process each missing season
        for season_number in missing_series.season_numbers:
            # Find the season in the series data
            season = next(
                (s for s in series_data.seasons if s.season_number == season_number),
                None,
            )
            if not season:
                self.logger.warning(
                    f"Season {season_number} not found in series {missing_series.id}"
                )
                continue

            # Check if a request already exists for this series and season
            stmt = select(SonarrRequest).where(
                SonarrRequest.sonarr_series_id == missing_series.id,
                SonarrRequest.season_number == season_number,
            )
            result = await self.db_session.execute(stmt)
            existing_request = result.scalars().first()

            # Convert episodes to SonarrEpisode objects
            sonarr_episodes = [
                SonarrEpisode(
                    sonarr_episode_id=episode.id,
                    episode_number=episode.episode_number,
                    absolute_episode_number=0,  # This information is not available in the current data
                    airDateUtc=0,  # This information is not available in the current data
                    hasFile=False,  # This information is not available in the current data
                    title="",  # This information is not available in the current data
                )
                for episode in season.episodes
            ]

            if existing_request:
                # Update existing request
                existing_request.is_missing = True
                existing_request.episodes = sonarr_episodes
            else:
                # Create new request
                new_request = SonarrRequest(
                    sonarr_series_id=missing_series.id,
                    tvdb_series_id=missing_series.tvdb_id,
                    season_number=season_number,
                    is_missing=True,
                    episodes=sonarr_episodes,
                )
                self.db_session.add(new_request)

        await self.db_session.commit()
