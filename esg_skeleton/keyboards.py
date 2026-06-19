from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from categories import CATEGORIES, CATEGORY_LABELS


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="💡 Подать ESG-идею")]],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отменить подачу")]],
        resize_keyboard=True,
    )


def category_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"category:{code}")]
            for code, label in CATEGORIES
        ]
    )


def review_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Название",   callback_data="edit:title"),
                InlineKeyboardButton(text="📂 Категория",  callback_data="edit:category"),
            ],
            [
                InlineKeyboardButton(text="❗ Проблема",   callback_data="edit:problem"),
                InlineKeyboardButton(text="💡 Решение",    callback_data="edit:solution"),
            ],
            [
                InlineKeyboardButton(text="📈 Эффект",     callback_data="edit:impact"),
                InlineKeyboardButton(text="🔧 Ресурсы",    callback_data="edit:resources"),
            ],
            [InlineKeyboardButton(text="✅ Отправить на модерацию", callback_data="submit:confirm")],
            [InlineKeyboardButton(text="❌ Отмена",                 callback_data="submit:cancel")],
        ]
    )
