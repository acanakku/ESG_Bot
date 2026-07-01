from __future__ import annotations

import sqlite3

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from bot.categories import CATEGORIES, category_title


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="Подать идею")],
        [KeyboardButton(text="База проектов"), KeyboardButton(text="Топ идей")],
        [KeyboardButton(text="Поиск"), KeyboardButton(text="Мои заявки")],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text="Модерация")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Отменить подачу")]], resize_keyboard=True)


def category_keyboard(prefix: str = "category") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=category.title, callback_data=f"{prefix}:{category.code}")]
            for category in CATEGORIES
        ]
    )


def category_filter_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="Все категории", callback_data="list:all")]]
    rows.extend(
        [InlineKeyboardButton(text=category_title(category.code), callback_data=f"list:{category.code}")]
        for category in CATEGORIES
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def review_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Название", callback_data="edit:title"),
                InlineKeyboardButton(text="Категория", callback_data="edit:category"),
            ],
            [
                InlineKeyboardButton(text="Проблема", callback_data="edit:problem"),
                InlineKeyboardButton(text="Решение", callback_data="edit:solution"),
            ],
            [
                InlineKeyboardButton(text="Эффект", callback_data="edit:impact"),
                InlineKeyboardButton(text="Ресурсы", callback_data="edit:resources"),
            ],
            [InlineKeyboardButton(text="Отправить на модерацию", callback_data="submit:confirm")],
            [InlineKeyboardButton(text="Отменить", callback_data="submit:cancel")],
        ]
    )


def idea_list_keyboard(
    ideas: list[sqlite3.Row],
    prefix: str = "idea",
    page_prefix: str | None = None,
    page: int = 0,
    has_next: bool = False,
) -> InlineKeyboardMarkup:
    rows = []
    for idea in ideas:
        title = idea["title"]
        if len(title) > 42:
            title = f"{title[:39]}..."
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"#{idea['id']} | {title} | рейтинг {idea['score']}",
                    callback_data=f"{prefix}:{idea['id']}",
                )
            ]
        )
    if page_prefix:
        navigation = []
        if page > 0:
            navigation.append(InlineKeyboardButton(text="Назад", callback_data=f"{page_prefix}:{page - 1}"))
        if has_next:
            navigation.append(InlineKeyboardButton(text="Дальше", callback_data=f"{page_prefix}:{page + 1}"))
        if navigation:
            rows.append(navigation)
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
