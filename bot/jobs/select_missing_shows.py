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
    if await SonarrReleaseSelect.objects.filter(is_finished=False).aexists():
        return

    season = await (
        SonarrMonitoredSeason.objects.filter(
            current_select__isnull=True, current_download__isnull=True
        )
        .select_related("series")
        .order_by("series_id", "season_number")
    ).afirst()

    chat_id = (await BotUser.objects.aget(username="zxibizz")).chat_id

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

    season.current_select = release_select
    await season.asave()

    await create_sonarr_show_image(context.bot, release_select)
    await create_sonarr_show_description(context.bot, release_select)
    if not prowlarr_results:
        # TODO: message with custom search suggestion
        release_select.is_finished = True
        await release_select.asave()
        await context.bot.send_message(
            release_select.chat_id, "Не удалось найти подходящих релизов =("
        )
        return

    release_select.select_message_id = await create_sonarr_release_select(
        context.bot, release_select
    )
    await release_select.asave()
