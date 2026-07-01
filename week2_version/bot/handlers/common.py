from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.formatters import idea_card, status_label
from bot.keyboards import category_filter_keyboard, idea_actions_keyboard, idea_list_keyboard, main_menu
from bot.services.database import Database
from bot.states import SearchForm

router = Router()
PAGE_SIZE = 8


def is_admin(user_id: int | None, settings: Settings) -> bool:
    return bool(user_id and user_id in settings.admin_ids)


async def register_user(message: Message, db: Database) -> None:
    user = message.from_user
    if not user:
        return
    await db.upsert_user(user.id, user.username, user.full_name)


async def send_idea_list(
    message: Message,
    db: Database,
    title: str,
    page_prefix: str,
    page: int = 0,
    category: str | None = None,
    search: str | None = None,
    sort: str = "newest",
) -> None:
    rows = await db.list_ideas(
        status="approved",
        category=category,
        search=search,
        sort=sort,
        limit=PAGE_SIZE + 1,
        offset=page * PAGE_SIZE,
    )
    ideas = rows[:PAGE_SIZE]
    if not ideas:
        await message.answer("Пока ничего не найдено.")
        return
    await message.answer(
        f"{title}\nСтраница {page + 1}",
        reply_markup=idea_list_keyboard(
            ideas,
            page_prefix=page_prefix,
            page=page,
            has_next=len(rows) > PAGE_SIZE,
        ),
    )


@router.message(CommandStart())
async def start(message: Message, db: Database, settings: Settings) -> None:
    await register_user(message, db)
    user_is_admin = is_admin(message.from_user.id if message.from_user else None, settings)
    await message.answer(
        "Привет! Это ESG Idea Bot, версия второй недели.\n\n"
        "Здесь уже можно подать инициативу, пройти модерацию, смотреть одобренные проекты, искать идеи и голосовать.",
        reply_markup=main_menu(user_is_admin),
    )


@router.message(Command("help"))
async def help_command(message: Message, db: Database) -> None:
    await register_user(message, db)
    await message.answer(
        "/submit - подать ESG-идею\n"
        "/projects - база одобренных проектов\n"
        "/top - идеи по рейтингу\n"
        "/search - поиск по базе проектов\n"
        "/my - мои заявки и статусы\n"
        "/moderate - очередь модерации, только для админов\n"
        "/stats - статистика, только для админов\n"
        "/cancel - отменить текущее действие"
    )


@router.message(Command("projects"))
@router.message(F.text == "База проектов")
async def projects(message: Message, db: Database) -> None:
    await register_user(message, db)
    await message.answer("Выберите категорию одобренных проектов:", reply_markup=category_filter_keyboard())


@router.callback_query(F.data.startswith("list:"))
async def list_by_category(callback: CallbackQuery, db: Database) -> None:
    category = callback.data.split(":", 1)[1]
    if callback.message:
        await send_idea_list(
            callback.message,
            db,
            "Одобренные ESG-проекты",
            f"page:list:{category}",
            category=None if category == "all" else category,
        )
    await callback.answer()


@router.callback_query(F.data.startswith("page:list:"))
async def list_page(callback: CallbackQuery, db: Database) -> None:
    _, _, category, raw_page = callback.data.split(":")
    if callback.message:
        await send_idea_list(
            callback.message,
            db,
            "Одобренные ESG-проекты",
            f"page:list:{category}",
            page=int(raw_page),
            category=None if category == "all" else category,
        )
    await callback.answer()


@router.message(Command("top"))
@router.message(F.text == "Топ идей")
async def top_ideas(message: Message, db: Database) -> None:
    await register_user(message, db)
    await send_idea_list(message, db, "Лучшие идеи по рейтингу", "page:top", sort="rating")


@router.callback_query(F.data.startswith("page:top:"))
async def top_page(callback: CallbackQuery, db: Database) -> None:
    page = int(callback.data.split(":")[2])
    if callback.message:
        await send_idea_list(callback.message, db, "Лучшие идеи по рейтингу", "page:top", page=page, sort="rating")
    await callback.answer()


@router.message(Command("search"))
@router.message(F.text == "Поиск")
async def search_start(message: Message, state: FSMContext, db: Database) -> None:
    await register_user(message, db)
    await state.set_state(SearchForm.query)
    await message.answer("Напишите ключевое слово для поиска по одобренным идеям.")


@router.message(SearchForm.query)
async def search_query(message: Message, state: FSMContext, db: Database) -> None:
    if not message.text or len(message.text.strip()) < 2:
        await message.answer("Введите минимум 2 символа.")
        return
    query = message.text.strip()
    await state.update_data(search_query=query)
    await send_idea_list(message, db, f"Результаты поиска: {query}", "page:search", search=query, sort="rating")


@router.callback_query(F.data.startswith("page:search:"))
async def search_page(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    query = data.get("search_query")
    if not query:
        await callback.answer("Поиск устарел. Запустите /search заново.", show_alert=True)
        return
    page = int(callback.data.split(":")[2])
    if callback.message:
        await send_idea_list(callback.message, db, f"Результаты поиска: {query}", "page:search", page=page, search=query, sort="rating")
    await callback.answer()


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
        comment = f"\nКомментарий: {idea['moderator_comment']}" if idea["moderator_comment"] else ""
        lines.append(f"\n#{idea['id']} | {idea['title']}\nСтатус: {status_label(idea['status'])}\nРейтинг: {idea['score']}{comment}")
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
