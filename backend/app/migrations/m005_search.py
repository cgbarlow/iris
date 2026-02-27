"""Migration 005: FTS5 full-text search indexes."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m005_search"

UP_SQL = """
-- FTS5 virtual table for entity search
CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(
    entity_id UNINDEXED,
    name,
    entity_type UNINDEXED,
    description,
    tokenize='porter unicode61'
);

-- FTS5 virtual table for model search
CREATE VIRTUAL TABLE IF NOT EXISTS models_fts USING fts5(
    model_id UNINDEXED,
    name,
    model_type UNINDEXED,
    description,
    tokenize='porter unicode61'
);
"""


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up."""
    await db.executescript(UP_SQL)
    await db.commit()
