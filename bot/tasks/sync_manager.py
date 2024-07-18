import django  # noqa

django.setup()

from telegram.ext import Application

from admin.app.models import SonarrMonitoredSeason, SonarrSeries
from bot.sonarr import SonarrApiClient
from bot.sonarr import SonarrSeries as SonarrSeriesData
from bot.tvdb import TVDBApiClient, TVDBShow


class SyncManager:
    def __init__(
        self,
        sonarr_client: SonarrApiClient,
        tvdb_client: TVDBApiClient,
        application: Application,
    ) -> None:
        self._sonarr_client = sonarr_client
        self._tvdb_client = tvdb_client
        self._application = application

    async def sync(self):
        await self._sync_missing_series()

    async def _sync_missing_series(self):
        missing_series_data = await self._sonarr_client.get_missing()

        for missing_series in missing_series_data:
            series_data: SonarrSeriesData = await self._sonarr_client.get_series(
                missing_series.series_id
            )
            try:
                await SonarrSeries.objects.aget(series_id=missing_series.series_id)
            except SonarrSeries.DoesNotExist:
                tvdb_data: TVDBShow = await self._tvdb_client.get_series(
                    series_data.tvdb_id
                )
                await SonarrSeries.objects.acreate(
                    series_id=missing_series.series_id,
                    path=series_data.path,
                    tvdb_id=series_data.tvdb_id,
                    tvdb_year=tvdb_data.year,
                    tvdb_country=tvdb_data.country,
                    tvdb_title=tvdb_data.title,
                    tvdb_image_url=tvdb_data.image_url,
                    tvdb_overview=tvdb_data.overview,
                )

            season_data = None
            for season in series_data.seasons:
                if season.season_number == missing_series.season_number:
                    season_data = season

            await SonarrMonitoredSeason.objects.filter(
                series_id=missing_series.series_id
            ).aupdate_or_create(
                series_id=missing_series.series_id,
                season_number=missing_series.season_number,
                episode_file_count=season_data.episode_file_count,
                episode_count=season_data.episode_count,
                total_episodes_count=season_data.total_episodes_count,
                previous_airing=season_data.previous_airing,
            )


if __name__ == "__main__":
    import asyncio

    from bot.sonarr import SonarrApiClient
    from bot.tvdb import TVDBApiClient

    client = SyncManager(SonarrApiClient(), TVDBApiClient(), None)
    asyncio.run(client.sync())
