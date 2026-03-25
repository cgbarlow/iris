"""Migration 031: Create extensions registry table."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Create extensions table for the extension registry."""
    # Guard: skip if extensions table already exists
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='extensions'"
    )
    if await cursor.fetchone():
        return

    await db.execute(
        "CREATE TABLE IF NOT EXISTS extensions ("
        "  id TEXT PRIMARY KEY,"
        "  name TEXT NOT NULL UNIQUE,"
        "  description TEXT,"
        "  version TEXT NOT NULL,"
        "  is_enabled INTEGER NOT NULL DEFAULT 1,"
        "  installed_at TEXT NOT NULL,"
        "  installed_by TEXT NOT NULL,"
        "  updated_at TEXT NOT NULL,"
        "  config TEXT DEFAULT '{}'"
        ")"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_extensions_name ON extensions(name)"
    )

    await db.commit()
