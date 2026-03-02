"""Migration 012: Add sets table and set_id columns to models and entities.

Per ADR-060 (Sets, Batch Operations).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

DEFAULT_SET_ID = "00000000-0000-0000-0000-000000000001"


async def up(db: aiosqlite.Connection) -> None:
    """Create sets table, seed Default set, add set_id to models and entities."""
    # Create sets table
    await db.execute(
        "CREATE TABLE IF NOT EXISTS sets ("
        "  id TEXT PRIMARY KEY,"
        "  name TEXT NOT NULL UNIQUE,"
        "  description TEXT,"
        "  created_at TEXT NOT NULL,"
        "  created_by TEXT NOT NULL,"
        "  updated_at TEXT NOT NULL,"
        "  is_deleted INTEGER NOT NULL DEFAULT 0"
        ")"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_sets_name ON sets(name)"
    )

    # Seed Default set
    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "INSERT OR IGNORE INTO sets (id, name, description, created_at, created_by, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (DEFAULT_SET_ID, "Default", "Default set for all items", now, "system", now),
    )

    # Add set_id to models (idempotent)
    cursor = await db.execute("PRAGMA table_info(models)")
    columns = [row[1] for row in await cursor.fetchall()]
    if "set_id" not in columns:
        await db.execute(
            "ALTER TABLE models ADD COLUMN set_id TEXT REFERENCES sets(id)"
        )
        await db.execute(
            f"UPDATE models SET set_id = ? WHERE set_id IS NULL",  # noqa: S608
            (DEFAULT_SET_ID,),
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_models_set ON models(set_id)"
        )

    # Add set_id to entities (idempotent)
    cursor = await db.execute("PRAGMA table_info(entities)")
    columns = [row[1] for row in await cursor.fetchall()]
    if "set_id" not in columns:
        await db.execute(
            "ALTER TABLE entities ADD COLUMN set_id TEXT REFERENCES sets(id)"
        )
        await db.execute(
            f"UPDATE entities SET set_id = ? WHERE set_id IS NULL",  # noqa: S608
            (DEFAULT_SET_ID,),
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_entities_set ON entities(set_id)"
        )

    await db.commit()
