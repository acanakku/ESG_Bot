from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    code: str
    title: str


CATEGORIES: tuple[Category, ...] = (
    Category("environment", "Экология"),
    Category("social", "Социальное развитие"),
    Category("governance", "Управление"),
    Category("education", "Образование"),
    Category("innovation", "Инновации"),
)

CATEGORY_BY_CODE = {category.code: category for category in CATEGORIES}


def category_title(code: str) -> str:
    category = CATEGORY_BY_CODE.get(code)
    return category.title if category else code.title()
