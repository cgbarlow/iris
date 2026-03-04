"""Migration 009: Model tags table."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Create model_tags table."""
    # Guard: skip if m016 naming rename has already been applied
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='elements'"
    )
    if await cursor.fetchone():
        return
    await db.execute(
        "CREATE TABLE IF NOT EXISTS model_tags ("
        "  model_id TEXT NOT NULL,"
        "  tag TEXT NOT NULL,"
        "  created_at TEXT NOT NULL,"
        "  created_by TEXT,"
        "  PRIMARY KEY (model_id, tag),"
        "  FOREIGN KEY (model_id) REFERENCES models(id)"
        ")"
    )
    await db.commit()
