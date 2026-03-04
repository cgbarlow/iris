"""Migration 008: Entity tags table."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Create entity_tags table."""
    # Guard: skip if m016 naming rename has already been applied
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='elements'"
    )
    if await cursor.fetchone():
        return
    await db.execute(
        "CREATE TABLE IF NOT EXISTS entity_tags ("
        "  entity_id TEXT NOT NULL,"
        "  tag TEXT NOT NULL,"
        "  created_at TEXT NOT NULL,"
        "  created_by TEXT,"
        "  PRIMARY KEY (entity_id, tag),"
        "  FOREIGN KEY (entity_id) REFERENCES entities(id)"
        ")"
    )
    await db.commit()
