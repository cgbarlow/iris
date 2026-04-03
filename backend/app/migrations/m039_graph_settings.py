"""Migration 039: Graph display settings per scope.

Stores graph display preferences (visible node/edge types, physics
multipliers) scoped to global, collection, or set level.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m039_graph_settings"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up."""
    # Guard: skip if graph_settings table already exists
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='graph_settings'"
    )
    if await cursor.fetchone():
        return

    await db.execute(
        "CREATE TABLE IF NOT EXISTS graph_settings ("
        "  scope_type TEXT NOT NULL CHECK(scope_type IN ('global','collection','set')),"
        "  scope_id TEXT NOT NULL,"
        "  settings_json TEXT NOT NULL,"
        "  updated_at TEXT,"
        "  updated_by TEXT,"
        "  PRIMARY KEY (scope_type, scope_id)"
        ")"
    )
    await db.commit()
