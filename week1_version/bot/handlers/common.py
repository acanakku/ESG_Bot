from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.formatters import idea_card
from bot.keyboards import idea_actions_keyboard, idea_list_keyboard, main_menu
from bot.services.database import Database

router = Router()


def is_admin(user_id: int | None, settings: Settings) -> bool:
    return bool(user_id and user_id in settings.admin_ids)


async def register_user(message: Message, db: Database) -> None:
    user = message.from_user
    if not user:
        return
    await db.upsert_user(user.id, user.username, user.full_name)


@router.message(CommandStart())
async def start(message: Message, db: Database, settings: Settings) -> None:
    await register_user(message, db)
    user_is_admin = is_admin(message.from_user.id if message.from_user else None, settings)
    await message.answer(
        "Привет! Это бот для сбора ESG-идей.\n\n"
        "Можно подать инициативу, посмотреть одобренные проекты и проголосовать за лучшие.",
        reply_markup=main_menu(is_admin=user_is_admin),
    )


@router.message(Command("help"))
async def help_command(message: Message, db: Database) -> None:
    await register_user(message, db)
    await message.answer(
        "/submit - подать ESG-идею\n"
        "/projects - база одобренных проектов\n"
        "/my - мои заявки\n"
        "/moderate - очередь модерации, только для админов"
    )


@router.message(Command("projects"))
@router.message(F.text == "База проектов")
async def projects(message: Message, db: Database) -> None:
    await register_user(message, db)
    ideas = await db.list_ideas(status="approved")
    if not ideas:
        await message.answer("Пока нет одобренных проектов.")
        return
    await message.answer("Одобренные ESG-проекты:", reply_markup=idea_list_keyboard(ideas, "idea"))


@router.message(Command("my"))
@router.message(F.text == "Мои заявки")
async def my_ideas(message: Message, db: Database) -> None:
    await register_user(message, db)
    if not message.from_user:
        return
    ideas = await db.list_ideas(author_id=message.from_user.id)
    if not ideas:
        await message.answer("Вы еще не подавали идеи.")
        return
    lines = ["Ваши заявки:"]
    for idea in ideas:
        lines.append(f"#{idea['id']} | {idea['title']} | статус: {idea['status']} | рейтинг: {idea['score']}")
    await message.answer("\n".join(lines))


@router.callback_query(F.data.startswith("idea:"))
async def open_idea(callback: CallbackQuery, db: Database) -> None:
    if not callback.from_user:
        return
    idea_id = int(callback.data.split(":", 1)[1])
    idea = await db.get_idea(idea_id, callback.from_user.id)
    if not idea or idea["status"] != "approved":
        await callback.answer("Идея не найдена или еще не одобрена.", show_alert=True)
        return
    if callback.message:
        await callback.message.answer(
            idea_card(idea),
            reply_markup=idea_actions_keyboard(idea["id"], idea["score"], bool(idea["viewer_voted"])),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("vote:"))
async def vote(callback: CallbackQuery, db: Database) -> None:
    if not callback.from_user:
        return
    idea_id = int(callback.data.split(":", 1)[1])
    idea = await db.get_idea(idea_id, callback.from_user.id)
    if not idea or idea["status"] != "approved":
        await callback.answer("Голосовать можно только за одобренные идеи.", show_alert=True)
        return
    if idea["author_id"] == callback.from_user.id:
        await callback.answer("Нельзя голосовать за свою идею.", show_alert=True)
        return
    voted = await db.toggle_vote(idea_id, callback.from_user.id)
    refreshed = await db.get_idea(idea_id, callback.from_user.id)
    if refreshed and callback.message:
        await callback.message.edit_reply_markup(
            reply_markup=idea_actions_keyboard(refreshed["id"], refreshed["score"], bool(refreshed["viewer_voted"]))
        )
    await callback.answer("Голос добавлен" if voted else "Голос снят")
