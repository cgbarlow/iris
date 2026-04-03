"""Migration 038: Extend bookmarks to support elements.

Adds element_id column alongside existing diagram_id and package_id.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m038_element_bookmarks"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up."""
    cursor = await db.execute("PRAGMA table_info(bookmarks)")
    columns = [row[1] for row in await cursor.fetchall()]
    if "element_id" in columns:
        return

    await db.execute("ALTER TABLE bookmarks ADD COLUMN element_id TEXT REFERENCES elements(id)")
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_bookmarks_element ON bookmarks(element_id)"
    )
    await db.commit()
