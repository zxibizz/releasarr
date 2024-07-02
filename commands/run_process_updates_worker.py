import pickle

import django

django.setup()

import asyncio
import logging
import signal

import aiokafka
from telegram import Update

from bot.app import get_application

logger = logging.getLogger("commands.run_bot")


def get_shutdown_sig_handler(lock: asyncio.Lock):
    def _shutdown_sig_handler(signum, frame):
        signal_code = signal.Signals(signum)
        logger.info(f"Received {signal_code.name}")
        lock.release()

    return _shutdown_sig_handler


async def main():
    shutdown_signal_lock = asyncio.Lock()
    await shutdown_signal_lock.acquire()

    consumer = aiokafka.AIOKafkaConsumer(
        "bot_updates",
        bootstrap_servers="localhost:9092",
        group_id="my_group",
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )

    signal.signal(signal.SIGINT, get_shutdown_sig_handler(shutdown_signal_lock))
    application = await get_application()
    async with application:
        logger.info("Starting...")
        await application.start()

        logger.info("Started! Serving....")

        # application.job_queue.run_once(sync_missing_shows, when=0)
        async with consumer:
            async for msg in consumer:
                try:
                    update = Update.de_json(
                        pickle.loads(msg.value),
                        application.bot,
                    )
                except Exception:
                    print("Failed to parse", msg)
                    await consumer.commit()
                    continue

                await application.process_update(update)
                await consumer.commit()
                if not shutdown_signal_lock.locked():
                    break

        logger.info("Shutting down...")
        # await application.stop()


if __name__ == "__main__":
    asyncio.run(main())
