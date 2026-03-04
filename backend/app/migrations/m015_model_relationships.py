"""Migration m015: Create model_relationships table for inter-model dependencies."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Create model_relationships table."""
    # Guard: skip if m016 naming rename has already been applied
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='elements'"
    )
    if await cursor.fetchone():
        return

    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='model_relationships'"
    )
    if await cursor.fetchone():
        return

    await db.execute("""
        CREATE TABLE model_relationships (
            id TEXT PRIMARY KEY,
            source_model_id TEXT NOT NULL REFERENCES models(id) ON DELETE CASCADE,
            target_model_id TEXT NOT NULL REFERENCES models(id) ON DELETE CASCADE,
            relationship_type TEXT NOT NULL,
            label TEXT,
            description TEXT,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(source_model_id, target_model_id, relationship_type)
        )
    """)
    await db.execute(
        "CREATE INDEX idx_model_rel_source ON model_relationships(source_model_id)"
    )
    await db.execute(
        "CREATE INDEX idx_model_rel_target ON model_relationships(target_model_id)"
    )
    await db.commit()
