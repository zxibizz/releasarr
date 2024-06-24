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
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from admin.app.models import Chat
from bot.tvdb import TVDBApiClient

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
tvdb_client = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await Chat.objects.aget_or_create(id=update.effective_chat.id)
    user = update.effective_user
    await update.message.reply_text(rf"Hi {user.mention_html()}!")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message with three inline buttons attached."""

    await Log.objects.acreate(text=update.message.text)
    keyboard = [
        [
            InlineKeyboardButton("То что нужно", callback_data="1"),
            InlineKeyboardButton("Другие варианты (4)", callback_data="2"),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    searching_message = await update.message.reply_text("Searching for the show...")

    results = (
        await asyncio.gather(tvdb_client.search(update.message.text), asyncio.sleep(2))
    )[0]
    if not results:
        await searching_message.edit_text(
            f"Couldn't find any matches for '{searching_message.text}'"
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


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()

    await query.edit_message_text(text=f"Selected option: {query.data}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays info on how to use the bot."""
    await update.message.reply_text("Use /start to test this bot.")


async def init_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    global tvdb_client
    tvdb_client = TVDBApiClient()
