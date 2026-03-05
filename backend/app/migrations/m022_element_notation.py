"""Migration 022: Add notation column to elements table (ADR-081)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Add notation column to elements table."""
    cursor = await db.execute("PRAGMA table_info(elements)")
    columns = [row[1] for row in await cursor.fetchall()]
    if "notation" not in columns:
        await db.execute(
            "ALTER TABLE elements ADD COLUMN notation TEXT DEFAULT 'simple'"
        )
        await db.commit()
