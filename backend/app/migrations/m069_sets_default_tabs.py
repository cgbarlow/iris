"""Migration 069: per-set tab defaults (ADR-204).

Adds two TEXT columns to ``sets`` so each set chooses which tab is
active by default on:

- ``/packages/{id}`` — ``package_tab_default`` (relationships|details).
- ``/views/{id}``    — ``view_tab_default`` (canvas|relationships|details).

Enums are enforced at the application layer (Pydantic ``Literal``)
rather than via SQL CHECK constraints, to keep the SQLite ↔ Supabase
syntax identical (Protocol §15).

Defaults are the new desired defaults (relationships for packages,
canvas for views), so existing rows inherit them with no back-fill.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m069_sets_default_tabs"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up. Idempotent — checks for column presence."""
    cursor = await db.execute("PRAGMA table_info(sets)")
    cols = {row[1] for row in await cursor.fetchall()}
    if "package_tab_default" not in cols:
        await db.execute(
            "ALTER TABLE sets ADD COLUMN package_tab_default "
            "TEXT NOT NULL DEFAULT 'relationships'"
        )
    if "view_tab_default" not in cols:
        await db.execute(
            "ALTER TABLE sets ADD COLUMN view_tab_default "
            "TEXT NOT NULL DEFAULT 'canvas'"
        )
    await db.commit()
