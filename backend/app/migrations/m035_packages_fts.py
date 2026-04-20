"""Migration 035: Create packages_fts FTS5 virtual table for package search."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Create packages_fts FTS5 table if it does not exist."""
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='packages_fts'"
    )
    if await cursor.fetchone():
        return  # Already exists

    await db.execute("""
        CREATE VIRTUAL TABLE packages_fts USING fts5(
            package_id UNINDEXED,
            name,
            description
        )
    """)
    await db.commit()
