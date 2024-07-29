from dataclasses import dataclass

from admin.app.models import SonarrMonitoredSeason, SonarrSeries
from bot.config import get_dependecies
from bot.dependencies.sonarr import SonarrApiClient
from bot.dependencies.sonarr import SonarrSeries as SonarrSeriesData
from bot.dependencies.tvdb import TVDBApiClient, TVDBShow


@dataclass
class SyncManagerResult:
    sonarr_updated: bool
    radarr_updated: bool


class SyncManager:
    async def sync(self):
        return SyncManagerResult(
            await self._sync_sonarr_missing(),
            await self._sync_radarr_missing(),
        )

    async def _sync_sonarr_missing(self) -> bool:
        dependencies = get_dependecies()
        missing_series_data = await dependencies.sonarr_api_client.get_missing()

        for missing_series in missing_series_data:
            series_data: SonarrSeriesData = (
                await dependencies.sonarr_api_client.get_series(
                    missing_series.series_id
                )
            )
            try:
                await SonarrSeries.objects.aget(series_id=missing_series.series_id)
            except SonarrSeries.DoesNotExist:
                tvdb_data: TVDBShow = await dependencies.tvdb_api_client.get_series(
                    series_data.tvdb_id
                )
                await SonarrSeries.objects.acreate(
                    series_id=missing_series.series_id,
                    path=series_data.path,
                    tvdb_id=series_data.tvdb_id,
                    tvdb_year=tvdb_data.year,
                    tvdb_country=tvdb_data.country,
                    tvdb_title=tvdb_data.title,
                    tvdb_title_en=tvdb_data.title_en,
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

        return len(missing_series_data) > 0

    async def _sync_radarr_missing(self) -> bool:
        return False


if __name__ == "__main__":
    import asyncio

    from bot.dependencies.sonarr import SonarrApiClient
    from bot.dependencies.tvdb import TVDBApiClient

    client = SyncManager(SonarrApiClient(), TVDBApiClient(), None)
    asyncio.run(client.sync())
