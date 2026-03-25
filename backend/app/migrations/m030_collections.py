"""Migration 030: Add collections table and collection_id to sets/ai_conversations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Create collections table and add collection_id to sets and ai_conversations."""
    # Guard: skip if collections table already exists
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='collections'"
    )
    if await cursor.fetchone():
        return

    # Create collections table
    await db.execute(
        "CREATE TABLE IF NOT EXISTS collections ("
        "  id TEXT PRIMARY KEY,"
        "  name TEXT NOT NULL,"
        "  description TEXT,"
        "  created_at TEXT,"
        "  created_by TEXT,"
        "  updated_at TEXT,"
        "  is_deleted INTEGER DEFAULT 0,"
        "  thumbnail_source TEXT,"
        "  thumbnail_diagram_id TEXT,"
        "  thumbnail_image BLOB"
        ")"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_collections_name ON collections(name)"
    )
    await db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_collections_name_active "
        "ON collections(name) WHERE is_deleted = 0"
    )

    # Add collection_id to sets (idempotent)
    cursor = await db.execute("PRAGMA table_info(sets)")
    columns = [row[1] for row in await cursor.fetchall()]
    if "collection_id" not in columns:
        await db.execute(
            "ALTER TABLE sets ADD COLUMN collection_id TEXT REFERENCES collections(id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_sets_collection ON sets(collection_id)"
        )

    # Add collection_id to ai_conversations (idempotent)
    cursor = await db.execute("PRAGMA table_info(ai_conversations)")
    columns = [row[1] for row in await cursor.fetchall()]
    if "collection_id" not in columns:
        await db.execute(
            "ALTER TABLE ai_conversations ADD COLUMN collection_id TEXT"
        )

    await db.commit()
