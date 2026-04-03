"""Migration 037: Create sets_fts and collections_fts FTS5 virtual tables."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Create FTS5 tables for sets and collections if they do not exist."""
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='sets_fts'"
    )
    if not await cursor.fetchone():
        await db.execute("""
            CREATE VIRTUAL TABLE sets_fts USING fts5(
                set_id UNINDEXED,
                name,
                description
            )
        """)

    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='collections_fts'"
    )
    if not await cursor.fetchone():
        await db.execute("""
            CREATE VIRTUAL TABLE collections_fts USING fts5(
                collection_id UNINDEXED,
                name,
                description
            )
        """)

    await db.commit()
