from telegram.ext import CallbackContext

from admin.app.models import BotUser, SonarrMonitoredSeason, SonarrReleaseSelect
from bot.config import get_dependecies
from bot.messages import (
    create_sonarr_release_select,
    create_sonarr_show_description,
    create_sonarr_show_image,
)


async def select_missing_shows(context: CallbackContext):
    dependencies = get_dependecies()
    seasons_to_select = (
        SonarrMonitoredSeason.objects.filter(
            current_select__isnull=True, current_download__isnull=True
        )
        .select_related("series")
        .order_by("series_id", "season_number")
    )[:2]

    chat_id = (await BotUser.objects.aget(username="zxibizz")).chat_id
    described_shows = set()

    async for season in seasons_to_select:
        prowlarr_results = await dependencies.prowlarr_api_client.search(
            season.series.tvdb_title + " " + str(season.season_number)
        )
        if not prowlarr_results:
            prowlarr_results = await dependencies.prowlarr_api_client.search(
                season.series.tvdb_title_en + " " + str(season.season_number)
            )
        release_select = await SonarrReleaseSelect.objects.acreate(
            season=season,
            prowlarr_results=prowlarr_results,
            chat_id=chat_id,
        )
        if not prowlarr_results:
            continue  # TODO: message with custom search suggestion

        if season.series.id not in described_shows:
            await create_sonarr_show_image(context.bot, release_select)
            await create_sonarr_show_description(context.bot, release_select)
            described_shows.add(season.series.id)
        select_message_id = await create_sonarr_release_select(
            context.bot, release_select
        )
        release_select.select_message_id = select_message_id
        await release_select.asave()

    # SonarrMonitoredSeason.objects.filter(
    #     episode_file_count__lt=F("episode_count")
    # )
