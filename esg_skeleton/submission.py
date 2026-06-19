"""
submission.py — полный цикл подачи ESG-идеи.

Идеи сохраняются в ideas.json рядом со скриптом.
Чтобы подключить реальную БД — замените функцию save_idea().
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from categories import CATEGORY_LABELS
from keyboards import cancel_keyboard, category_keyboard, main_menu, review_keyboard
from states import IdeaForm

router = Router()
log = logging.getLogger(__name__)

IDEAS_FILE = Path("ideas.json")

# ──────────────────────────────────────────────
# Хранилище (замените на БД по необходимости)
# ──────────────────────────────────────────────

def save_idea(user_id: int, data: dict) -> int:
    """Сохраняет идею в ideas.json и возвращает её порядковый номер."""
    ideas: list[dict] = []
    if IDEAS_FILE.exists():
        ideas = json.loads(IDEAS_FILE.read_text(encoding="utf-8"))
    idea = {
        "id": len(ideas) + 1,
        "user_id": user_id,
        "title": data.get("title", ""),
        "category": data.get("category", ""),
        "problem": data.get("problem", ""),
        "solution": data.get("solution", ""),
        "impact": data.get("impact", ""),
        "resources": data.get("resources", ""),
        "status": "submitted",
    }
    ideas.append(idea)
    IDEAS_FILE.write_text(json.dumps(ideas, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Idea #%d saved from user %d", idea["id"], user_id)
    return idea["id"]


# ──────────────────────────────────────────────
# Вспомогательные функции
# ──────────────────────────────────────────────

def idea_preview(data: dict) -> str:
    cat_label = CATEGORY_LABELS.get(data.get("category", ""), data.get("category", "—"))
    return (
        "📋 Проверьте вашу ESG-инициативу перед отправкой:\n\n"
        f"📌 Название: {data.get('title', '')}\n"
        f"📂 Категория: {cat_label}\n\n"
        f"❗ Проблема:\n{data.get('problem', '')}\n\n"
        f"💡 Решение:\n{data.get('solution', '')}\n\n"
        f"📈 Ожидаемый эффект:\n{data.get('impact', '')}\n\n"
        f"🔧 Нужные ресурсы:\n{data.get('resources', '')}"
    )


async def show_review(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(IdeaForm.review)
    await message.answer(idea_preview(data), reply_markup=review_keyboard())


async def finish_or_edit(message: Message, state: FSMContext, next_state, next_prompt: str) -> None:
    """После каждого шага: либо возвращает на превью (режим редактирования), либо идёт дальше."""
    data = await state.get_data()
    if data.get("edit_field"):
        await state.update_data(edit_field=None)
        await show_review(message, state)
        return
    await state.set_state(next_state)
    await message.answer(next_prompt, reply_markup=cancel_keyboard())


# ──────────────────────────────────────────────
# Отмена
# ──────────────────────────────────────────────

@router.message(StateFilter(IdeaForm), Command("cancel"))
@router.message(StateFilter(IdeaForm), F.text == "❌ Отменить подачу")
async def cancel_submission(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Подача отменена.", reply_markup=main_menu())


# ──────────────────────────────────────────────
# Шаг 0: старт
# ──────────────────────────────────────────────

@router.message(Command("submit"))
@router.message(F.text == "💡 Подать ESG-идею")
async def submit_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(IdeaForm.title)
    await message.answer(
        "Шаг 1/6 — Напишите короткое название вашей идеи.\n\n"
        "Форму можно остановить командой /cancel или кнопкой ниже.",
        reply_markup=cancel_keyboard(),
    )


# ──────────────────────────────────────────────
# Шаг 1: название
# ──────────────────────────────────────────────

@router.message(IdeaForm.title)
async def submit_title(message: Message, state: FSMContext) -> None:
    if not message.text or len(message.text.strip()) < 5:
        await message.answer("Название должно содержать не менее 5 символов.")
        return
    await state.update_data(title=message.text.strip())
    data = await state.get_data()
    if data.get("edit_field"):
        await state.update_data(edit_field=None)
        await show_review(message, state)
        return
    await state.set_state(IdeaForm.category)
    await message.answer("Шаг 2/6 — Выберите ESG-категорию:", reply_markup=cancel_keyboard())
    await message.answer("Категории:", reply_markup=category_keyboard())


# ──────────────────────────────────────────────
# Шаг 2: категория
# ──────────────────────────────────────────────

@router.callback_query(IdeaForm.category, F.data.startswith("category:"))
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
    cat_label = CATEGORY_LABELS.get(category, category)
    if callback.message:
        await callback.message.answer(
            f"Категория: {cat_label}\n\nШаг 3/6 — Какую проблему решает эта инициатива?",
            reply_markup=cancel_keyboard(),
        )
    await callback.answer()


@router.message(IdeaForm.category)
async def category_text_blocked(message: Message) -> None:
    await message.answer("Выберите категорию кнопкой выше или отмените форму через /cancel.")


# ──────────────────────────────────────────────
# Шаг 3: проблема
# ──────────────────────────────────────────────

@router.message(IdeaForm.problem)
async def submit_problem(message: Message, state: FSMContext) -> None:
    if not message.text or len(message.text.strip()) < 20:
        await message.answer("Опишите проблему подробнее (не менее 20 символов).")
        return
    await state.update_data(problem=message.text.strip())
    await finish_or_edit(message, state, IdeaForm.solution, "Шаг 4/6 — Опишите предлагаемое решение.")


# ──────────────────────────────────────────────
# Шаг 4: решение
# ──────────────────────────────────────────────

@router.message(IdeaForm.solution)
async def submit_solution(message: Message, state: FSMContext) -> None:
    if not message.text or len(message.text.strip()) < 20:
        await message.answer("Опишите решение подробнее (не менее 20 символов).")
        return
    await state.update_data(solution=message.text.strip())
    await finish_or_edit(message, state, IdeaForm.impact, "Шаг 5/6 — Какой измеримый ESG-эффект вы ожидаете?")


# ──────────────────────────────────────────────
# Шаг 5: эффект
# ──────────────────────────────────────────────

@router.message(IdeaForm.impact)
async def submit_impact(message: Message, state: FSMContext) -> None:
    if not message.text or len(message.text.strip()) < 10:
        await message.answer("Опишите ожидаемый эффект (не менее 10 символов).")
        return
    await state.update_data(impact=message.text.strip())
    await finish_or_edit(message, state, IdeaForm.resources, "Шаг 6/6 — Какие ресурсы или партнёры нужны?")


# ──────────────────────────────────────────────
# Шаг 6: ресурсы
# ──────────────────────────────────────────────

@router.message(IdeaForm.resources)
async def submit_resources(message: Message, state: FSMContext) -> None:
    if not message.text or len(message.text.strip()) < 5:
        await message.answer("Укажите хотя бы один ресурс или партнёра (не менее 5 символов).")
        return
    await state.update_data(resources=message.text.strip())
    await show_review(message, state)


# ──────────────────────────────────────────────
# Превью и редактирование
# ──────────────────────────────────────────────

@router.message(IdeaForm.review)
async def review_text_blocked(message: Message) -> None:
    await message.answer("Используйте кнопки выше или отмените форму через /cancel.")


FIELD_PROMPTS = {
    "title":     "Отправьте новое название идеи.",
    "problem":   "Отправьте обновлённое описание проблемы.",
    "solution":  "Отправьте обновлённое решение.",
    "impact":    "Отправьте обновлённый ожидаемый эффект.",
    "resources": "Отправьте обновлённые ресурсы или партнёров.",
}


@router.callback_query(IdeaForm.review, F.data.startswith("edit:"))
async def edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    field = callback.data.split(":", 1)[1]
    await state.update_data(edit_field=field)
    if field == "category":
        await state.set_state(IdeaForm.category)
        if callback.message:
            await callback.message.answer("Выберите новую категорию:", reply_markup=cancel_keyboard())
            await callback.message.answer("Категории:", reply_markup=category_keyboard())
    else:
        await state.set_state(getattr(IdeaForm, field))
        if callback.message:
            await callback.message.answer(FIELD_PROMPTS[field], reply_markup=cancel_keyboard())
    await callback.answer()


# ──────────────────────────────────────────────
# Подтверждение / финальная отмена
# ──────────────────────────────────────────────

@router.callback_query(IdeaForm.review, F.data == "submit:confirm")
async def confirm_submission(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.from_user:
        return
    data = await state.get_data()
    idea_id = save_idea(callback.from_user.id, data)
    await state.clear()
    if callback.message:
        await callback.message.answer(
            f"✅ Ваша ESG-инициатива #{idea_id} отправлена на модерацию!\n\n"
            "После одобрения она появится в базе проектов.",
            reply_markup=main_menu(),
        )
    await callback.answer("Отправлено!")


@router.callback_query(IdeaForm.review, F.data == "submit:cancel")
async def cancel_from_review(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message:
        await callback.message.answer("Подача отменена.", reply_markup=main_menu())
    await callback.answer()
