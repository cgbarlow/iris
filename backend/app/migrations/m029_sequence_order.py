"""Migration 029: Add sequence_order column to diagrams and packages tables."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Add sequence_order column to diagrams and packages for user-controllable ordering."""
    # Check if column already exists on diagrams
    cursor = await db.execute("PRAGMA table_info(diagrams)")
    columns = [row[1] for row in await cursor.fetchall()]
    if "sequence_order" in columns:
        return

    await db.execute(
        "ALTER TABLE diagrams ADD COLUMN sequence_order INTEGER NOT NULL DEFAULT 0"
    )
    await db.execute(
        "ALTER TABLE packages ADD COLUMN sequence_order INTEGER NOT NULL DEFAULT 0"
    )

    # Backfill existing rows by rowid to preserve creation order
    await db.execute(
        "UPDATE diagrams SET sequence_order = rowid"
    )
    await db.execute(
        "UPDATE packages SET sequence_order = rowid"
    )
    await db.commit()
