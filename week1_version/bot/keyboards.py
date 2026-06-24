from __future__ import annotations

import sqlite3

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from bot.categories import CATEGORIES, category_title


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="Подать идею")],
        [KeyboardButton(text="База проектов"), KeyboardButton(text="Мои заявки")],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text="Модерация")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def category_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=category.title, callback_data=f"category:{category.code}")]
            for category in CATEGORIES
        ]
    )


def review_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Отправить на модерацию", callback_data="submit:confirm")],
            [InlineKeyboardButton(text="Отменить", callback_data="submit:cancel")],
        ]
    )


def idea_list_keyboard(ideas: list[sqlite3.Row], prefix: str) -> InlineKeyboardMarkup:
    rows = []
    for idea in ideas:
        title = idea["title"]
        if len(title) > 40:
            title = f"{title[:37]}..."
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"#{idea['id']} | {title} | рейтинг {idea['score']}",
                    callback_data=f"{prefix}:{idea['id']}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def idea_actions_keyboard(idea_id: int, score: int, voted: bool) -> InlineKeyboardMarkup:
    text = f"{'Снять голос' if voted else 'Голосовать'} | рейтинг {score}"
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=f"vote:{idea_id}")]])


def moderation_keyboard(idea_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Одобрить", callback_data=f"moderate:approve:{idea_id}"),
                InlineKeyboardButton(text="Отклонить", callback_data=f"moderate:reject:{idea_id}"),
            ]
        ]
    )
