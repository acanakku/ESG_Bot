from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import load_settings
from bot.handlers import admin, common, submission
from bot.services.database import Database


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()
    db = Database(settings.database_path)
    await db.init()

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())
    dp["settings"] = settings
    dp["db"] = db

    dp.include_router(submission.router)
    dp.include_router(admin.router)
    dp.include_router(common.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
