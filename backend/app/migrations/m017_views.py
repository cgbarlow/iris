"""Migration 017: Create views table for admin-configurable views (ADR-075)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Create views table."""
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='views'"
    )
    if await cursor.fetchone():
        return

    await db.execute("""
        CREATE TABLE views (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            config TEXT NOT NULL DEFAULT '{}',
            is_default INTEGER NOT NULL DEFAULT 0,
            created_by TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    await db.commit()
