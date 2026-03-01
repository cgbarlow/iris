"""Migration 010: Add theme support to model_thumbnails (composite PK)."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Add theme column to model_thumbnails with composite PK (model_id, theme).

    SQLite does not support ALTER TABLE to change a PRIMARY KEY, so we
    create a new table, copy existing rows (defaulting theme to 'dark'),
    drop the old table, and rename.
    """
    # Check if migration already applied (theme column exists)
    cursor = await db.execute("PRAGMA table_info(model_thumbnails)")
    columns = [row[1] for row in await cursor.fetchall()]
    if "theme" in columns:
        return

    await db.execute(
        "CREATE TABLE IF NOT EXISTS model_thumbnails_new ("
        "  model_id TEXT NOT NULL,"
        "  theme TEXT NOT NULL DEFAULT 'dark',"
        "  thumbnail BLOB NOT NULL,"
        "  updated_at TEXT NOT NULL,"
        "  PRIMARY KEY (model_id, theme),"
        "  FOREIGN KEY (model_id) REFERENCES models(id)"
        ")"
    )

    await db.execute(
        "INSERT OR IGNORE INTO model_thumbnails_new "
        "(model_id, theme, thumbnail, updated_at) "
        "SELECT model_id, 'dark', thumbnail, updated_at "
        "FROM model_thumbnails"
    )

    await db.execute("DROP TABLE model_thumbnails")
    await db.execute(
        "ALTER TABLE model_thumbnails_new RENAME TO model_thumbnails"
    )

    await db.commit()
