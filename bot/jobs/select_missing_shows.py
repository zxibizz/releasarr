from telegram.ext import CallbackContext

from admin.app.models import BotUser, SonarrMonitoredSeason, SonarrReleaseSelect
from bot.config import get_dependecies
from bot.messages import create_sonarr_show_description, create_sonarr_show_image


async def select_missing_shows(context: CallbackContext):
    dependencies = get_dependecies()
    seasons_to_select = SonarrMonitoredSeason.objects.filter(
        current_select__isnull=True, current_download__isnull=True
    ).select_related("series")

    chat_id = (await BotUser.objects.aget(username="zxibizz")).chat_id

    async for season in seasons_to_select:
        prowlarr_results = await dependencies.prowlarr_api_client.search(
            season.series.tvdb_title + " " + str(season.season_number)
        )
        release_select = await SonarrReleaseSelect.objects.acreate(
            season=season,
            prowlarr_results=prowlarr_results,
            chat_id=chat_id,
        )
        image_message_id = await create_sonarr_show_image(context.bot, release_select)
        description_message_id = await create_sonarr_show_description(
            context.bot, release_select
        )
        # keyboard_message_id = await create_sonarr_select_release_keyboard(
        #     context.bot, release_select
        # )
        release_select.image_message_id = image_message_id
        release_select.description_message_id = description_message_id
        await release_select.asave()

    # SonarrMonitoredSeason.objects.filter(
    #     episode_file_count__lt=F("episode_count")
    # )
