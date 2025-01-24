from src.application.interfaces.db_manager import I_DBManager
from src.application.interfaces.series_service import (
    I_SeriesService,
    MissingSeries,
    Series,
)
from src.application.interfaces.shows_repository import I_ShowsRepository
from src.application.interfaces.tvdb_client import I_TvdbClient, TvdbShowData
from src.application.models import Show


class UseCase_SyncMissingSeries:
    def __init__(
        self,
        db_manager: I_DBManager,
        series_service: I_SeriesService,
        shows_repository: I_ShowsRepository,
        tvdb_client: I_TvdbClient,
    ) -> None:
        self.db_manager = db_manager
        self.series_service = series_service
        self.shows_repository = shows_repository
        self.tvdb_client = tvdb_client

    async def process(self):
        missing_seriess = await self.series_service.get_missing()
        async with self.db_manager.begin_session() as db_session:
            with db_session.no_autoflush:
                await self.shows_repository.unflag_all_missing_series(db_session)
                for missing_series in missing_seriess:
                    show = await self.shows_repository.get_series(
                        db_session=db_session, series_id=missing_series.id
                    )
                    if not show:
                        show = await self._create_new_show(missing_series)
                    else:
                        show = await self._update_show(show, missing_series)

                    show.is_missing = True
                    show.missing_seasons = missing_series.season_numbers

                    await self.shows_repository.save(db_session=db_session, show=show)

    async def _create_new_show(self, missing_series: MissingSeries) -> Show:
        tvdb_data: TvdbShowData = await self.tvdb_client.get_series(
            missing_series.tvdb_id
        )
        series_data: Series = await self.series_service.get_series(
            series_id=missing_series.id
        )
        show = Show(
            sonarr_id=missing_series.id,
            tvdb_data_raw=tvdb_data.model_dump_json(),
            sonarr_data_raw=series_data.model_dump_json(),
        )
        show.prowlarr_search = show.tvdb_data.title
        show.prowlarr_data_raw = None

        return show

    async def _update_show(self, show: Show, missing_series: MissingSeries) -> None:
        tvdb_data: TvdbShowData = await self.tvdb_client.get_series(
            missing_series.tvdb_id
        )
        series_data: Series = await self.series_service.get_series(
            series_id=missing_series.id
        )
        show.tvdb_data_raw = tvdb_data.model_dump_json()
        show.sonarr_data_raw = series_data.model_dump_json()

        return show
