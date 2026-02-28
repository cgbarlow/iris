"""Migration 008: Entity tags table."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Create entity_tags table."""
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
