from __future__ import annotations

import sqlite3
from pathlib import Path

import aiosqlite


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def init(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(
                """
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS ideas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    author_id INTEGER NOT NULL REFERENCES users(telegram_id),
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    problem TEXT NOT NULL,
                    solution TEXT NOT NULL,
                    impact TEXT NOT NULL,
                    resources TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'submitted',
                    moderator_id INTEGER,
                    moderator_comment TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS votes (
                    idea_id INTEGER NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
                    user_id INTEGER NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (idea_id, user_id)
                );

                CREATE INDEX IF NOT EXISTS idx_ideas_status ON ideas(status);
                CREATE INDEX IF NOT EXISTS idx_ideas_author ON ideas(author_id);
                CREATE INDEX IF NOT EXISTS idx_votes_idea ON votes(idea_id);
                """
            )
            await db.commit()

    async def upsert_user(self, telegram_id: int, username: str | None, full_name: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO users (telegram_id, username, full_name)
                VALUES (?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    username = excluded.username,
                    full_name = excluded.full_name
                """,
                (telegram_id, username, full_name),
            )
            await db.commit()

    async def create_idea(self, author_id: int, data: dict[str, str]) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO ideas (author_id, title, category, problem, solution, impact, resources)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    author_id,
                    data["title"],
                    data["category"],
                    data["problem"],
                    data["solution"],
                    data["impact"],
                    data["resources"],
                ),
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def list_ideas(self, status: str | None = None, author_id: int | None = None) -> list[sqlite3.Row]:
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("i.status = ?")
            params.append(status)
        if author_id:
            clauses.append("i.author_id = ?")
            params.append(author_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        async with aiosqlite.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute(
                f"""
                SELECT i.*, u.full_name AS author_name, COUNT(v.user_id) AS score
                FROM ideas i
                JOIN users u ON u.telegram_id = i.author_id
                LEFT JOIN votes v ON v.idea_id = i.id
                {where}
                GROUP BY i.id
                ORDER BY i.created_at DESC
                """,
                params,
            )
            return await cursor.fetchall()

    async def get_idea(self, idea_id: int, viewer_id: int | None = None) -> sqlite3.Row | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute(
                """
                SELECT
                    i.*,
                    u.full_name AS author_name,
                    COUNT(v.user_id) AS score,
                    EXISTS(
                        SELECT 1 FROM votes own
                        WHERE own.idea_id = i.id AND own.user_id = ?
                    ) AS viewer_voted
                FROM ideas i
                JOIN users u ON u.telegram_id = i.author_id
                LEFT JOIN votes v ON v.idea_id = i.id
                WHERE i.id = ?
                GROUP BY i.id
                """,
                (viewer_id, idea_id),
            )
            return await cursor.fetchone()

    async def set_status(self, idea_id: int, status: str, moderator_id: int, comment: str = "") -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                UPDATE ideas
                SET status = ?,
                    moderator_id = ?,
                    moderator_comment = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, moderator_id, comment, idea_id),
            )
            await db.commit()

    async def toggle_vote(self, idea_id: int, user_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT 1 FROM votes WHERE idea_id = ? AND user_id = ?",
                (idea_id, user_id),
            )
            exists = await cursor.fetchone()
            if exists:
                await db.execute("DELETE FROM votes WHERE idea_id = ? AND user_id = ?", (idea_id, user_id))
                await db.commit()
                return False
            await db.execute("INSERT INTO votes (idea_id, user_id) VALUES (?, ?)", (idea_id, user_id))
            await db.commit()
            return True

    async def stats(self) -> sqlite3.Row:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute(
                """
                SELECT
                    COUNT(*) AS total_ideas,
                    SUM(status = 'approved') AS approved_ideas,
                    SUM(status = 'submitted') AS submitted_ideas,
                    (SELECT COUNT(*) FROM votes) AS total_votes,
                    (SELECT COUNT(*) FROM users) AS total_users
                FROM ideas
                """
            )
            return await cursor.fetchone()
