"""Migration 007: Model thumbnails table for PNG storage."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Create model_thumbnails table."""
    await db.execute(
        "CREATE TABLE IF NOT EXISTS model_thumbnails ("
        "  model_id TEXT PRIMARY KEY,"
        "  thumbnail BLOB NOT NULL,"
        "  updated_at TEXT NOT NULL,"
        "  FOREIGN KEY (model_id) REFERENCES models(id)"
        ")"
    )
    await db.commit()
