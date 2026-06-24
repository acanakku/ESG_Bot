from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_path: Path
    admin_ids: set[int]


def _parse_admin_ids(raw_value: str) -> set[int]:
    admin_ids: set[int] = set()
    for item in raw_value.split(","):
        item = item.strip()
        if item:
            admin_ids.add(int(item))
    return admin_ids


def load_settings() -> Settings:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is required. Copy .env.example to .env and add your bot token.")

    return Settings(
        bot_token=token,
        database_path=Path(os.getenv("DATABASE_PATH", "data/week1_esg_ideas.db")),
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),
    )
