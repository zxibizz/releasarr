import logging
import os

from telegram.ext import Application, ContextTypes

from bot.context import AppContext
from bot.handlers import init_handlers

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
tvdb_client = None


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def get_application() -> Application:
    context_types = ContextTypes(context=AppContext)
    application = (
        Application.builder().token(TOKEN).context_types(context_types).build()
    )

    await init_handlers(application)

    return application
