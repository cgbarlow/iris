"""Migration 033: Add mode and thread_id columns to ai_conversations (SQLite)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Add mode and thread_id columns to ai_conversations."""
    cursor = await db.execute("PRAGMA table_info(ai_conversations)")
    columns = {row[1] for row in await cursor.fetchall()}

    if "mode" not in columns:
        await db.execute(
            "ALTER TABLE ai_conversations ADD COLUMN mode TEXT DEFAULT 'discuss'"
        )

    if "thread_id" not in columns:
        await db.execute(
            "ALTER TABLE ai_conversations ADD COLUMN thread_id TEXT"
        )

    await db.commit()
