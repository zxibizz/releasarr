#!/usr/bin/env python
# pylint: disable=unused-argument
# This program is dedicated to the public domain under the CC0 license.

"""
Basic example for a bot that uses inline keyboards. For an in-depth explanation, check out
 https://github.com/python-telegram-bot/python-telegram-bot/wiki/InlineKeyboard-Example.
"""

import asyncio
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
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
from bot.context import AppContext
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


async def echo(update: Update, context: AppContext) -> None:
    """Sends a message with three inline buttons attached."""

    search = await Search.objects.acreate(
        bot_user=context.bot_user,
        query=update.message.text,
        status="searching",
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "То что нужно",
                callback_data={
                    "search_id": search.id,
                    "command": "search_pick_match",
                    "choice": "pick",
                    "index": 0,
                },
            ),
            InlineKeyboardButton(
                "Другие варианты (4)",
                callback_data={
                    "search_id": search.id,
                    "command": "search_pick_match",
                    "choice": "goto",
                    "index": 1,
                },
            ),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    searching_message = await update.message.reply_text("Ищем...")

    results = (
        await asyncio.gather(tvdb_client.search(update.message.text), asyncio.sleep(2))
    )[0]

    search.results = results
    search.results_count = len(results)
    if not results:
        search.status = "no results"
        await search.asave()
        await searching_message.edit_text(
            f"Не удалось найти '{searching_message.text}' =("
        )
        return
    await searching_message.delete()

    current_index = 0
    show = results[current_index]

    title = show["title_rus"] or show["title_eng"] or show["title"]
    overview = show["overview_rus"] or show["overview_eng"] or show["overview"]

    if show["image_url"]:
        tvdb_image_message = await update.message.reply_photo(show["image_url"])
    tvdb_pick_message = await update.message.reply_text(
        text=f'{title}\nГод {show["year"]}, Страна Япония\n\n{overview}',
        reply_markup=reply_markup,
    )

    search.status = "waiting for match choice"
    search.image_message_id = tvdb_image_message.id
    search.content_message_id = tvdb_pick_message.id
    await search.asave()


async def button(update: Update, context: AppContext) -> None:
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()

    await query.edit_message_text(text=f"Selected option: {query.data}")
    await context.drop_callback_data(query)


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
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    global tvdb_client
    tvdb_client = TVDBApiClient()
