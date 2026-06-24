from __future__ import annotations

import sqlite3
from html import escape

from bot.categories import category_title


def h(value: object) -> str:
    return escape("" if value is None else str(value), quote=False)


def idea_card(row: sqlite3.Row) -> str:
    return (
        f"ESG-идея #{row['id']}\n"
        f"{h(row['title'])}\n\n"
        f"Категория: {category_title(row['category'])}\n"
        f"Автор: {h(row['author_name'])}\n"
        f"Статус: {h(row['status'])}\n"
        f"Рейтинг: {row['score']}\n\n"
        f"Проблема:\n{h(row['problem'])}\n\n"
        f"Решение:\n{h(row['solution'])}\n\n"
        f"Ожидаемый эффект:\n{h(row['impact'])}\n\n"
        f"Ресурсы:\n{h(row['resources'])}"
    )
