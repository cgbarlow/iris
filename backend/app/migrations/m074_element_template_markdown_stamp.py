"""Migration 074: ``markdown_stamp`` column on ``element_templates`` (ADR-211).

Adds a TEXT column that stores a smart-markdown fragment using
``{{self:<field-spec>}}`` placeholders, substituted by the picker at
insert time. The seeded global stamps (m075) populate this column.

Idempotent — column-presence check.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m074_element_template_markdown_stamp"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up. Idempotent."""
    cursor = await db.execute("PRAGMA table_info(element_templates)")
    cols = {row[1] for row in await cursor.fetchall()}
    if "markdown_stamp" not in cols:
        await db.execute(
            "ALTER TABLE element_templates ADD COLUMN markdown_stamp TEXT",
        )
    await db.commit()
