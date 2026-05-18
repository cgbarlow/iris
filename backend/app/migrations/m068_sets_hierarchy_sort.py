"""Migration 068: per-set hierarchy sort preference (ADR-202).

Adds a ``hierarchy_sort`` column to ``sets`` so each set can choose
how its diagram/package tree is ordered when surfaced in the
hierarchy views (dashboard, packages page, views page).

Values:

- ``manual``     — current behaviour (sequence_order with diagrams first).
- ``alpha``      — alphabetical by name (interleaves packages and diagrams).
- ``newest``     — created_at DESC.
- ``oldest``     — created_at ASC.

Enum is enforced at the application layer (Pydantic ``Literal``) rather
than via a SQL CHECK constraint, to keep the SQLite ↔ Supabase syntax
identical (Protocol §15).

Default is ``'manual'`` so every existing set keeps its current
ordering until the user opts in to something else.

No back-fill required — the column DEFAULT handles existing rows.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m068_sets_hierarchy_sort"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up. Idempotent — checks for column presence."""
    cursor = await db.execute("PRAGMA table_info(sets)")
    cols = {row[1] for row in await cursor.fetchall()}
    if "hierarchy_sort" not in cols:
        await db.execute(
            "ALTER TABLE sets ADD COLUMN hierarchy_sort "
            "TEXT NOT NULL DEFAULT 'manual'"
        )
    await db.commit()
