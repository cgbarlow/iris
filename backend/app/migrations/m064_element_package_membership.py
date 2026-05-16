"""Migration 064: Element → package optional membership (ADR-184).

Adds nullable ``package_id`` column to ``elements`` plus an index. No
back-fill — every existing element keeps ``package_id = NULL``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m064_element_package_membership"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up. Idempotent."""
    cursor = await db.execute("PRAGMA table_info(elements)")
    cols = {row[1] for row in await cursor.fetchall()}
    if "package_id" not in cols:
        await db.execute(
            "ALTER TABLE elements ADD COLUMN package_id TEXT REFERENCES packages(id)"
        )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_elements_package ON elements(package_id)"
    )
    await db.commit()
