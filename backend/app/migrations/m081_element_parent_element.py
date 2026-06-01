"""Migration 081: Element → parent element containment (ADR-231).

Adds nullable self-referencing ``parent_element_id`` column to ``elements``
plus an index. No back-fill — every existing element keeps
``parent_element_id = NULL``. This is the element-containment axis (an element
owns child elements), so Sparx EA ``nestedClassifier`` trees (e.g. the GEANZ
capability zone → capability → sub-capability hierarchy) import with depth.
Orthogonal to ``package_id`` (ADR-184) and ``detail_diagram_id`` (ADR-221);
carried on the element row, not versioned.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m081_element_parent_element"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up. Idempotent."""
    cursor = await db.execute("PRAGMA table_info(elements)")
    cols = {row[1] for row in await cursor.fetchall()}
    if "parent_element_id" not in cols:
        await db.execute(
            "ALTER TABLE elements ADD COLUMN parent_element_id TEXT "
            "REFERENCES elements(id)"
        )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_elements_parent_element "
        "ON elements(parent_element_id)"
    )
    await db.commit()
