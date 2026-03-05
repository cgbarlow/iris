"""Migration 024: Create themes table for visual theme system (ADR-084)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Create themes table."""
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='themes'"
    )
    if await cursor.fetchone():
        return

    await db.execute("""
        CREATE TABLE themes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            notation TEXT NOT NULL,
            config TEXT NOT NULL DEFAULT '{}',
            is_default INTEGER NOT NULL DEFAULT 0,
            created_by TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    await db.commit()
