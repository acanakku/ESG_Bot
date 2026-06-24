from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.categories import category_title
from bot.handlers.common import register_user
from bot.keyboards import category_keyboard, main_menu, review_keyboard
from bot.services.database import Database
from bot.states import IdeaForm

router = Router()


def idea_preview(data: dict[str, str]) -> str:
    return (
        "Проверьте заявку перед отправкой на модерацию.\n\n"
        f"Название: {data.get('title', '')}\n"
        f"Категория: {category_title(data.get('category', ''))}\n\n"
        f"Проблема:\n{data.get('problem', '')}\n\n"
        f"Решение:\n{data.get('solution', '')}\n\n"
        f"Ожидаемый эффект:\n{data.get('impact', '')}\n\n"
        f"Ресурсы:\n{data.get('resources', '')}"
    )


@router.message(Command("submit"))
@router.message(F.text == "Подать идею")
async def submit_start(message: Message, state: FSMContext, db: Database) -> None:
    await register_user(message, db)
    await state.clear()
    await state.set_state(IdeaForm.title)
    await message.answer("Шаг 1/6. Отправьте короткое название ESG-идеи.")


@router.message(IdeaForm.title)
async def submit_title(message: Message, state: FSMContext) -> None:
    if not message.text or len(message.text.strip()) < 5:
        await message.answer("Название должно быть не короче 5 символов.")
        return
    await state.update_data(title=message.text.strip())
    await state.set_state(IdeaForm.category)
    await message.answer("Шаг 2/6. Выберите категорию:", reply_markup=category_keyboard())


@router.callback_query(IdeaForm.category, F.data.startswith("category:"))
async def submit_category(callback: CallbackQuery, state: FSMContext) -> None:
    category = callback.data.split(":", 1)[1]
    await state.update_data(category=category)
    await state.set_state(IdeaForm.problem)
    if callback.message:
        await callback.message.answer(
            f"Категория: {category_title(category)}\n\n"
            "Шаг 3/6. Какую проблему решает идея?"
        )
    await callback.answer()


@router.message(IdeaForm.problem)
async def submit_problem(message: Message, state: FSMContext) -> None:
    if not message.text or len(message.text.strip()) < 15:
        await message.answer("Опишите проблему подробнее.")
        return
    await state.update_data(problem=message.text.strip())
    await state.set_state(IdeaForm.solution)
    await message.answer("Шаг 4/6. Опишите предлагаемое решение.")


@router.message(IdeaForm.solution)
async def submit_solution(message: Message, state: FSMContext) -> None:
    if not message.text or len(message.text.strip()) < 15:
        await message.answer("Опишите решение подробнее.")
        return
    await state.update_data(solution=message.text.strip())
    await state.set_state(IdeaForm.impact)
    await message.answer("Шаг 5/6. Какой ESG-эффект ожидается?")


@router.message(IdeaForm.impact)
async def submit_impact(message: Message, state: FSMContext) -> None:
    if not message.text or len(message.text.strip()) < 10:
        await message.answer("Опишите ожидаемый эффект подробнее.")
        return
    await state.update_data(impact=message.text.strip())
    await state.set_state(IdeaForm.resources)
    await message.answer("Шаг 6/6. Какие ресурсы или партнеры нужны?")


@router.message(IdeaForm.resources)
async def submit_resources(message: Message, state: FSMContext) -> None:
    if not message.text or len(message.text.strip()) < 3:
        await message.answer("Укажите хотя бы один ресурс или вид поддержки.")
        return
    await state.update_data(resources=message.text.strip())
    await state.set_state(IdeaForm.review)
    await message.answer(idea_preview(await state.get_data()), reply_markup=review_keyboard())


@router.callback_query(IdeaForm.review, F.data == "submit:confirm")
async def confirm_submission(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    if not callback.from_user:
        return
    data = await state.get_data()
    idea_id = await db.create_idea(callback.from_user.id, data)
    await state.clear()
    if callback.message:
        await callback.message.answer(
            f"Идея #{idea_id} отправлена на модерацию.",
            reply_markup=main_menu(),
        )
    await callback.answer("Отправлено")


@router.callback_query(IdeaForm.review, F.data == "submit:cancel")
async def cancel_submission(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message:
        await callback.message.answer("Подача отменена.", reply_markup=main_menu())
    await callback.answer()


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Текущее действие отменено.", reply_markup=main_menu())
