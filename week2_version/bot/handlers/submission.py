from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.categories import category_title
from bot.config import Settings
from bot.formatters import submission_preview
from bot.handlers.common import is_admin, register_user
from bot.keyboards import cancel_keyboard, category_keyboard, main_menu, review_keyboard
from bot.services.content_filter import validate_text
from bot.services.database import Database
from bot.states import IdeaForm

router = Router()

FIELD_PROMPTS = {
    "title": "Отправьте новое короткое название ESG-идеи.",
    "problem": "Опишите проблему, которую решает идея.",
    "solution": "Опишите предлагаемое решение.",
    "impact": "Какой измеримый ESG-эффект ожидается?",
    "resources": "Какие ресурсы или партнеры нужны?",
}


async def show_review(message: Message, state: FSMContext) -> None:
    await state.set_state(IdeaForm.review)
    await message.answer(submission_preview(await state.get_data()), reply_markup=review_keyboard())


async def finish_field(message: Message, state: FSMContext, next_state, next_prompt: str) -> None:
    data = await state.get_data()
    if data.get("edit_field"):
        await state.update_data(edit_field=None)
        await show_review(message, state)
        return
    await state.set_state(next_state)
    await message.answer(next_prompt, reply_markup=cancel_keyboard())


@router.message(StateFilter(IdeaForm), Command("cancel"))
@router.message(StateFilter(IdeaForm), F.text == "Отменить подачу")
async def cancel_active_submission(message: Message, state: FSMContext, settings: Settings) -> None:
    await state.clear()
    user_id = message.from_user.id if message.from_user else None
    await message.answer("Подача идеи отменена.", reply_markup=main_menu(is_admin(user_id, settings)))


@router.message(Command("submit"))
@router.message(F.text == "Подать идею")
async def submit_start(message: Message, state: FSMContext, db: Database) -> None:
    await register_user(message, db)
    await state.clear()
    await state.set_state(IdeaForm.title)
    await message.answer("Шаг 1/6. Отправьте короткое название ESG-идеи.", reply_markup=cancel_keyboard())


@router.message(IdeaForm.title)
async def submit_title(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Нужно отправить текст.")
        return
    valid, reason = validate_text(message.text, min_chars=5)
    if not valid:
        await message.answer(reason)
        return
    await state.update_data(title=message.text.strip())
    await finish_field(message, state, IdeaForm.category, "Шаг 2/6. Выберите категорию:")
    data = await state.get_data()
    if not data.get("edit_field") and await state.get_state() == IdeaForm.category.state:
        await message.answer("Категории:", reply_markup=category_keyboard("submit_category"))


@router.callback_query(IdeaForm.category, F.data.startswith("submit_category:"))
async def submit_category(callback: CallbackQuery, state: FSMContext) -> None:
    category = callback.data.split(":", 1)[1]
    await state.update_data(category=category)
    data = await state.get_data()
    if data.get("edit_field"):
        await state.update_data(edit_field=None)
        if callback.message:
            await show_review(callback.message, state)
        await callback.answer()
        return
    await state.set_state(IdeaForm.problem)
    if callback.message:
        await callback.message.answer(
            f"Категория: {category_title(category)}\n\nШаг 3/6. Какую проблему решает идея?",
            reply_markup=cancel_keyboard(),
        )
    await callback.answer()


@router.message(IdeaForm.category)
async def category_requires_button(message: Message) -> None:
    await message.answer("Выберите категорию кнопкой под сообщением.")


@router.message(IdeaForm.problem)
async def submit_problem(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Нужно отправить текст.")
        return
    valid, reason = validate_text(message.text, min_chars=20)
    if not valid:
        await message.answer(reason)
        return
    await state.update_data(problem=message.text.strip())
    await finish_field(message, state, IdeaForm.solution, "Шаг 4/6. Опишите предлагаемое решение.")


@router.message(IdeaForm.solution)
async def submit_solution(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Нужно отправить текст.")
        return
    valid, reason = validate_text(message.text, min_chars=20)
    if not valid:
        await message.answer(reason)
        return
    await state.update_data(solution=message.text.strip())
    await finish_field(message, state, IdeaForm.impact, "Шаг 5/6. Какой ESG-эффект ожидается?")


@router.message(IdeaForm.impact)
async def submit_impact(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Нужно отправить текст.")
        return
    valid, reason = validate_text(message.text, min_chars=10)
    if not valid:
        await message.answer(reason)
        return
    await state.update_data(impact=message.text.strip())
    await finish_field(message, state, IdeaForm.resources, "Шаг 6/6. Какие ресурсы или партнеры нужны?")


@router.message(IdeaForm.resources)
async def submit_resources(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Нужно отправить текст.")
        return
    valid, reason = validate_text(message.text, min_chars=5)
    if not valid:
        await message.answer(reason)
        return
    await state.update_data(resources=message.text.strip())
    await show_review(message, state)


@router.callback_query(IdeaForm.review, F.data.startswith("edit:"))
async def edit_submission_field(callback: CallbackQuery, state: FSMContext) -> None:
    field = callback.data.split(":", 1)[1]
    await state.update_data(edit_field=field)
    if field == "category":
        await state.set_state(IdeaForm.category)
        if callback.message:
            await callback.message.answer("Выберите новую категорию:", reply_markup=category_keyboard("submit_category"))
    else:
        await state.set_state(getattr(IdeaForm, field))
        if callback.message:
            await callback.message.answer(FIELD_PROMPTS[field], reply_markup=cancel_keyboard())
    await callback.answer()


@router.callback_query(IdeaForm.review, F.data == "submit:confirm")
async def confirm_submission(callback: CallbackQuery, state: FSMContext, db: Database, settings: Settings) -> None:
    if not callback.from_user:
        return
    idea_id = await db.create_idea(callback.from_user.id, await state.get_data())
    await state.clear()
    if callback.message:
        await callback.message.answer(
            f"Идея #{idea_id} отправлена на модерацию.",
            reply_markup=main_menu(callback.from_user.id in settings.admin_ids),
        )
    await callback.answer("Отправлено")


@router.callback_query(IdeaForm.review, F.data == "submit:cancel")
async def cancel_submission_callback(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    await state.clear()
    if callback.message:
        await callback.message.answer(
            "Подача идеи отменена.",
            reply_markup=main_menu(callback.from_user.id in settings.admin_ids if callback.from_user else False),
        )
    await callback.answer()


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext, settings: Settings) -> None:
    await state.clear()
    user_id = message.from_user.id if message.from_user else None
    await message.answer("Текущее действие отменено.", reply_markup=main_menu(is_admin(user_id, settings)))
