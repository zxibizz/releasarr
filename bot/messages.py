import telegram
from telegram import (
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)

from admin.app.models import Search
from bot.callbacks import SearchGotoShow, SearchSelectShow, SearchShowNotSelected
from bot.prowlarr import ProwlarrRelease


class BaseMessage: ...


class SearchStarted:
    def __init__(self, search_message: Message):
        self._search_message = search_message
        self.message = None

    async def send(self) -> "SearchStarted":
        self.message = await self._search_message.reply_text(
            "Ищем...",
        )
        return self


class SearchNoShowsFound:
    def __init__(self, search_started_message: Message, query: str):
        self.query = query
        self._search_started_message = search_started_message

    async def send(self) -> "SearchStarted":
        await self._search_started_message.edit_text(
            f"Не удалось найти '{self.query}' =("
        )
        return self


class SearchSelectShowKeyboard:
    def __init__(self, bot: Bot, search: Search):
        self._bot = bot
        self._search = search
        self._show = search.results[0]
        self.show_image_message_id = None
        self.show_keyboard_message_id = None

    async def send(self) -> "SearchSelectShowKeyboard":
        await self._send_show_image_message()
        await self._send_show_keyboard_message()
        return self

    async def _send_show_image_message(self):
        self.show_image_message_id = (
            await self._bot.send_photo(
                self._search.chat_id,
                _build_image(self._show),
            )
        ).id

    async def _send_show_keyboard_message(self):
        self.show_keyboard_message_id = (
            await self._bot.send_message(
                chat_id=self._search.chat_id,
                text=_build_description(self._show, self._search, 0),
                reply_markup=InlineKeyboardMarkup(_build_keyboard(self._search, 0)),
            )
        ).id


class SearchSelectShowUpdateKeyboard:
    def __init__(self, bot: Bot, search: Search, index: int):
        self._bot = bot
        self._search = search
        self._index = index
        self._show = search.results[index]

    async def send(self) -> "SearchSelectShowUpdateKeyboard":
        await self._update_show_image_message()
        await self._update_show_keyboard_message()
        return self

    async def _update_show_image_message(self):
        try:
            await self._bot.edit_message_media(
                media=InputMediaPhoto(_build_image(self._show)),
                chat_id=self._search.chat_id,
                message_id=self._search.image_message_id,
            )
        except telegram.error.BadRequest:
            pass

    async def _update_show_keyboard_message(self):
        await self._bot.edit_message_text(
            chat_id=self._search.chat_id,
            message_id=self._search.content_message_id,
            text=_build_description(self._show, self._search, self._index),
            reply_markup=InlineKeyboardMarkup(
                _build_keyboard(self._search, self._index)
            ),
        )


class SearchSelectReleaseKeyboard:
    def __init__(self, bot: Bot, search: Search):
        self._bot = bot
        self._search = search
        self.release_keyboard_message_id: int = None

    async def send(self) -> "SearchSelectShowUpdateKeyboard":
        await self._bot.send_message(
            chat_id=self._search.chat_id,
            text=build_select_release_description(self._search, 0),
            reply_markup=InlineKeyboardMarkup(
                build_select_release_keyboard(self._search, 0)
            ),
        )

        return self


def build_select_release_description(search: Search, current_index: int):
    release: ProwlarrRelease = search.found_releases[current_index]
    releases_count = len(search.found_releases)
    lines = [
        f"Трекер: {release.indexer}",
        f"Возраст: {release.age} дней",
        f"Название: {release.title}",
        f"Размер: {release.size}",
        f"Пиры: {release.seeders}/{release.leechers}",
        f"Скачано: {release.grabs}",
        f"Ссылка: {release.info_url}",
        "",
        f"{current_index + 1} / {releases_count}",
    ]
    return "\n".join(lines)


def build_select_release_keyboard(search: Search, current_index: int):
    return []


def _build_image(show):
    if show["image_url"]:
        return show["image_url"]
    with open("static/preview_not_found.png", "rb") as file:
        return file.read()


def _build_description(show: dict, search: Search, index: int):
    title = show["title_rus"] or show["title_eng"] or show["title"]
    overview = show["overview_rus"] or show["overview_eng"] or show["overview"]
    if not overview:
        overview = "<Нет описания>"
    overview = overview[:200] + ("..." if len(overview) > 200 else "")

    description_rows = [
        title,
        f'Год {show["year"]}',
        "Страна Япония",
        "",
        overview,
        "",
        f"{index + 1} / {search.results_count}",
    ]
    return "\n".join(description_rows)


def _build_keyboard(search: Search, index: int):
    keyboard_header = [
        InlineKeyboardButton(
            "То что нужно",
            callback_data=SearchSelectShow(search.id, index),
        ),
    ]
    keyboard_footer = [
        InlineKeyboardButton(
            "Нет подходящего =(",
            callback_data=SearchShowNotSelected(search.id),
        )
    ]
    if search.results_count > index:
        keyboard_header.append(
            InlineKeyboardButton(
                ">>", callback_data=SearchGotoShow(search.id, index + 1)
            )
        )
    if index > 0:
        keyboard_footer.append(
            InlineKeyboardButton(
                "<<", callback_data=SearchGotoShow(search.id, index - 1)
            )
        )

    return [keyboard_header, keyboard_footer]
