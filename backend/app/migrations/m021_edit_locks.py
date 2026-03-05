"""Migration 021: Edit locks table for pessimistic locking (ADR-080)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Create the edit_locks table."""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS edit_locks (
            id TEXT PRIMARY KEY,
            target_type TEXT NOT NULL CHECK (target_type IN ('diagram', 'element', 'package')),
            target_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            username TEXT NOT NULL,
            acquired_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            last_heartbeat TEXT NOT NULL,
            UNIQUE (target_type, target_id)
        )
    """)
    await db.commit()
