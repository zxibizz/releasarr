import django

django.setup()

from telegram.ext import CallbackContext

from bot.config import get_dependecies
from bot.jobs.select_missing_shows import select_missing_shows


async def sync_missing_shows(context: CallbackContext):
    dependencies = get_dependecies()
    sync_result = await dependencies.sync_manager.sync()

    if sync_result.sonarr_updated:
        context.job_queue.run_once(select_missing_shows, 0)
