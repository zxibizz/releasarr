import django

django.setup()

import asyncio
import logging
import signal

from bot.app import get_application

logger = logging.getLogger("start_bot")


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
    application = await get_application()
    async with application:
        logger.info("Starting...")
        await application.start()
        await application.updater.start_polling()

        logger.info("Started! Serving....")

        await shutdown_signal_lock.acquire()

        logger.info("Shutting down...")
        await application.updater.stop()
        await application.stop()


if __name__ == "__main__":
    asyncio.run(main())
