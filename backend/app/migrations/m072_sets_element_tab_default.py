"""Migration 072: per-set element_tab_default (ADR-208).

Adds a TEXT column ``element_tab_default`` to ``sets`` so each set
chooses which tab is active by default on ``/elements/{id}``.

Values: ``details | diagrams | relationships | versions``. Enum is
enforced at the application layer (Pydantic ``Literal``) rather than
via SQL CHECK constraints, to keep the SQLite ↔ Supabase syntax
identical (Protocol §15).

Default is ``relationships`` per ADR-208, matching the v6.14.0
``package_tab_default`` choice.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m072_sets_element_tab_default"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up. Idempotent — checks for column presence."""
    cursor = await db.execute("PRAGMA table_info(sets)")
    cols = {row[1] for row in await cursor.fetchall()}
    if "element_tab_default" not in cols:
        await db.execute(
            "ALTER TABLE sets ADD COLUMN element_tab_default "
            "TEXT NOT NULL DEFAULT 'relationships'",
        )
    await db.commit()
