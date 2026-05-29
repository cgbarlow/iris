"""Migration 080: Element → detail diagram drill link (ADR-221).

Adds nullable ``detail_diagram_id`` column to ``elements`` plus an index.
No back-fill — every existing element keeps ``detail_diagram_id = NULL``.
This is the Sparx EA "composite element" drill: an element points at the
diagram that elaborates it. Carried on the element row (like
``package_id``, ADR-184), not versioned.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m080_element_detail_diagram"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up. Idempotent."""
    cursor = await db.execute("PRAGMA table_info(elements)")
    cols = {row[1] for row in await cursor.fetchall()}
    if "detail_diagram_id" not in cols:
        await db.execute(
            "ALTER TABLE elements ADD COLUMN detail_diagram_id TEXT "
            "REFERENCES diagrams(id)"
        )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_elements_detail_diagram "
        "ON elements(detail_diagram_id)"
    )
    await db.commit()
