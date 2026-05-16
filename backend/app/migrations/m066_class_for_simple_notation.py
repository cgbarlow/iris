"""Migration 066: Allow ``class`` diagram type under ``simple`` notation
(ADR-188, issue #160).

The base registry (m020) intentionally registered ``class`` only against
``uml``. Live data has elements with ``notation='simple'`` and
``element_type='class'`` (e.g. FIXM US Extension v4.1.1) that the
new-element diagram-type dropdown couldn't surface. This migration
inserts the missing (class, simple, is_default=0) pair so the dropdown
matches reality.

No schema changes — single idempotent row insert.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m066_class_for_simple_notation"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up. Idempotent — INSERT OR IGNORE on the new pair."""
    await db.execute(
        "INSERT OR IGNORE INTO diagram_type_notations "
        "(diagram_type_id, notation_id, is_default) VALUES (?, ?, ?)",
        ("class", "simple", 0),
    )
    await db.commit()
