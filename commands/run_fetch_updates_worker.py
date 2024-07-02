import django
from telegram import Bot

django.setup()

import asyncio
import logging
import os
import signal

from aiokafka import AIOKafkaProducer

logger = logging.getLogger("run_fetch_updates_worker")
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")


def get_shutdown_sig_handler(lock: asyncio.Lock):
    def _shutdown_sig_handler(signum, frame):
        signal_code = signal.Signals(signum)
        logger.info(f"Received {signal_code.name}")
        lock.release()

    return _shutdown_sig_handler


async def main():
    shutdown_signal_lock = asyncio.Lock()
    await shutdown_signal_lock.acquire()

    signal.signal(signal.SIGINT, get_shutdown_sig_handler(shutdown_signal_lock))

    bot = Bot(TOKEN)
    producer = AIOKafkaProducer(bootstrap_servers="localhost:9092")
    offset = None
    async with producer, bot:
        while True:
            if not shutdown_signal_lock.locked():
                break

            updates = await bot.get_updates(timeout=10, offset=offset)
            if not updates:
                continue

            for update in updates:
                await producer.send_and_wait(
                    "bot_updates",
                    value=update.to_json(),
                    key=str(update.effective_chat.id).encode(),
                )
                offset = update.update_id + 1


if __name__ == "__main__":
    asyncio.run(main())
