"""Migration 009: Model tags table."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Create model_tags table."""
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
