from typing import Optional, Tuple

from telegram.ext import BasePersistence


class DjangoPersistence(BasePersistence):
    async def get_bot_data(self):
        raise NotImplementedError

    async def update_bot_data(self, data):
        raise NotImplementedError

    async def refresh_bot_data(self, bot_data):
        raise NotImplementedError

    async def get_chat_data(self):
        raise NotImplementedError

    async def update_chat_data(self, chat_id: int, data):
        raise NotImplementedError

    async def refresh_chat_data(self, chat_id: int, chat_data):
        raise NotImplementedError

    async def get_user_data(self):
        raise NotImplementedError

    async def update_user_data(self, user_id: int, data):
        raise NotImplementedError

    async def refresh_user_data(self, user_id: int, user_data):
        raise NotImplementedError

    async def get_callback_data(self):
        print(self)
        # try:
        #     return CallbackData.objects.get(namespace=self._namespace).data
        # except CallbackData.DoesNotExist:
        #     return None

    async def update_callback_data(self, data):
        print(data)
        # CallbackData.objects.update_or_create(
        #     namespace=self._namespace, defaults={"data": data}
        # )

    async def get_conversations(self, name: str):
        raise NotImplementedError

    async def update_conversation(
        self, name: str, key: Tuple[int, ...], new_state: Optional[object]
    ):
        raise NotImplementedError

    async def flush(self):
        pass

    async def drop_chat_data(self, chat_id: int) -> None:
        pass

    async def drop_user_data(self, user_id: int) -> None:
        pass
