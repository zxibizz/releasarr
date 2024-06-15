from telegram.ext import CallbackContext

from admin.app.models import User


class AppContext(CallbackContext):
    bot_user: User
