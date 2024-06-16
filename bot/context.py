from telegram.ext import CallbackContext

from admin.app.models import BotUser


class AppContext(CallbackContext):
    bot_user: BotUser
