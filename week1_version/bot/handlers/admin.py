from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.formatters import idea_card
from bot.keyboards import idea_list_keyboard, main_menu, moderation_keyboard
from bot.services.database import Database
from bot.states import ModerationForm

router = Router()


def is_admin(user_id: int | None, settings: Settings) -> bool:
    return bool(user_id and user_id in settings.admin_ids)


@router.message(Command("moderate"))
@router.message(F.text == "Модерация")
async def moderation_queue(message: Message, db: Database, settings: Settings) -> None:
    if not is_admin(message.from_user.id if message.from_user else None, settings):
        await message.answer("Модерация доступна только администраторам.")
        return
    ideas = await db.list_ideas(status="submitted")
    if not ideas:
        await message.answer("Очередь модерации пуста.", reply_markup=main_menu(True))
        return
    await message.answer("Идеи на модерации:", reply_markup=idea_list_keyboard(ideas, "moderate_open"))


@router.message(Command("stats"))
async def stats(message: Message, db: Database, settings: Settings) -> None:
    if not is_admin(message.from_user.id if message.from_user else None, settings):
        await message.answer("Статистика доступна только администраторам.")
        return
    row = await db.stats()
    await message.answer(
        "Статистика:\n"
        f"Всего идей: {row['total_ideas'] or 0}\n"
        f"Одобрено: {row['approved_ideas'] or 0}\n"
        f"На модерации: {row['submitted_ideas'] or 0}\n"
        f"Голосов: {row['total_votes'] or 0}\n"
        f"Пользователей: {row['total_users'] or 0}"
    )


@router.callback_query(F.data.startswith("moderate_open:"))
async def open_for_moderation(callback: CallbackQuery, db: Database, settings: Settings) -> None:
    if not is_admin(callback.from_user.id if callback.from_user else None, settings):
        await callback.answer("Только для администраторов.", show_alert=True)
        return
    idea_id = int(callback.data.split(":", 1)[1])
    idea = await db.get_idea(idea_id, callback.from_user.id if callback.from_user else None)
    if not idea or idea["status"] != "submitted":
        await callback.answer("Идея не найдена или уже обработана.", show_alert=True)
        return
    if callback.message:
        await callback.message.answer(idea_card(idea), reply_markup=moderation_keyboard(idea["id"]))
    await callback.answer()


@router.callback_query(F.data.startswith("moderate:"))
async def moderate(callback: CallbackQuery, db: Database, settings: Settings, bot: Bot, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id if callback.from_user else None, settings):
        await callback.answer("Только для администраторов.", show_alert=True)
        return
    _, action, raw_idea_id = callback.data.split(":")
    idea_id = int(raw_idea_id)
    idea = await db.get_idea(idea_id, callback.from_user.id if callback.from_user else None)
    if not idea or idea["status"] != "submitted":
        await callback.answer("Идея не найдена или уже обработана.", show_alert=True)
        return

    if action == "reject":
        await state.set_state(ModerationForm.reject_comment)
        await state.update_data(reject_idea_id=idea_id)
        if callback.message:
            await callback.message.answer("Напишите причину отклонения.")
        await callback.answer()
        return

    await db.set_status(idea_id, "approved", callback.from_user.id, "")
    try:
        await bot.send_message(idea["author_id"], f"Ваша идея #{idea_id} одобрена.")
    except TelegramAPIError:
        pass
    if callback.message:
        await callback.message.answer(f"Идея #{idea_id} одобрена.")
    await callback.answer("Готово")


@router.message(ModerationForm.reject_comment)
async def reject_with_comment(message: Message, state: FSMContext, db: Database, settings: Settings, bot: Bot) -> None:
    if not is_admin(message.from_user.id if message.from_user else None, settings):
        await state.clear()
        await message.answer("Только для администраторов.")
        return
    if not message.text or len(message.text.strip()) < 3:
        await message.answer("Напишите короткую причину.")
        return
    data = await state.get_data()
    idea_id = int(data["reject_idea_id"])
    idea = await db.get_idea(idea_id, message.from_user.id if message.from_user else None)
    if not idea:
        await state.clear()
        await message.answer("Идея не найдена.")
        return
    await db.set_status(idea_id, "rejected", message.from_user.id, message.text.strip())
    await state.clear()
    try:
        await bot.send_message(
            idea["author_id"],
            f"Ваша идея #{idea_id} отклонена.\nПричина: {message.text.strip()}",
        )
    except TelegramAPIError:
        pass
    await message.answer(f"Идея #{idea_id} отклонена.")
