from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from dotenv import load_dotenv

import submission
from keyboards import main_menu


async def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN не задан. Создайте .env и добавьте токен.")

    bot = Bot(token=token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(submission.router)

    @dp.message(Command("start"))
    async def cmd_start(message: Message) -> None:
        await message.answer(
            "Добро пожаловать в ESG Idea Bot!\n\n"
            "Здесь можно подать ESG-инициативу для рассмотрения.",
            reply_markup=main_menu(),
        )

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
