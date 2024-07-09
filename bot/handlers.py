#!/usr/bin/env python
# pylint: disable=unused-argument
# This program is dedicated to the public domain under the CC0 license.

"""
Basic example for a bot that uses inline keyboards. For an in-depth explanation, check out
 https://github.com/python-telegram-bot/python-telegram-bot/wiki/InlineKeyboard-Example.
"""

import asyncio
import os

from telegram import (
    Update,
)
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    TypeHandler,
    filters,
)

from admin.app.models import BotUser, Search
from bot.callbacks import SearchGotoShow
from bot.context import AppContext
from bot.messages import (
    SearchNoShowsFound,
    SearchSelectShowKeyboard,
    SearchSelectShowUpdateKeyboard,
    SearchStarted,
)
from bot.tvdb import TVDBApiClient

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
tvdb_client = None


async def start(update: Update, context: AppContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_text(rf"Hi {user.mention_html()}!")


async def help_command(update: Update, context: AppContext) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")


async def search_handler(update: Update, context: AppContext) -> None:
    """Sends a message with three inline buttons attached."""

    search_message = update.message
    search = await Search.objects.acreate(
        chat_id=update.effective_chat.id,
        query=search_message.text,
        status="searching",
    )

    search_started_message = (await SearchStarted(search_message).send()).message

    results = (
        await asyncio.gather(
            tvdb_client.search(search_message.text),
            asyncio.sleep(2),
        )
    )[0]

    search.results = results
    search.results_count = len(results)
    if not results:
        search.status = "no results"
        await search.asave()
        await SearchNoShowsFound(search_started_message, search_message.text).send()
        return
    await search_started_message.delete()

    keyboard = await SearchSelectShowKeyboard(context.bot, search).send()

    search.status = "waiting for match choice"
    search.image_message_id = keyboard.show_image_message_id
    search.content_message_id = keyboard.show_keyboard_message_id
    await search.asave()


async def search_goto_show(update: Update, context: AppContext) -> None:
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()

    callback: SearchGotoShow = query.data
    search: Search = await Search.objects.aget(id=callback.search_id)

    await SearchSelectShowUpdateKeyboard(
        context.bot,
        search,
        callback.index,
    ).send()

    context.drop_callback_data(query)


async def help_command(update: Update, context: AppContext) -> None:
    """Displays info on how to use the bot."""
    await update.message.reply_text("Use /start to test this bot.")


async def track_users(update: Update, context: AppContext) -> None:
    """Store the user id of the incoming update, if any."""
    if not update.effective_user:
        update.message.reply_text(
            "Currently the bot does not support non private chats"
        )
        raise ApplicationHandlerStop

    context.bot_user, _ = await BotUser.objects.aget_or_create(
        chat_id=update.effective_chat.id,
        defaults={
            "first_name": update.effective_user.first_name,
            "last_name": update.effective_user.last_name,
            "username": update.effective_user.username,
            "language_code": update.effective_user.language_code,
        },
    )


async def init_handlers(application: Application) -> None:
    application.add_handler(TypeHandler(Update, track_users), group=-1)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(search_goto_show, SearchGotoShow))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler)
    )

    global tvdb_client
    tvdb_client = TVDBApiClient()
