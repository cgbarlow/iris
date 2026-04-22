"""Migration 040: Expanded AI diagram creation prompts (ADR-132, SPEC-132-A).

Seeds 11 new rows in ai_creation_prompts that scale the DoView AI creation
framework (ADR-094) out to Simple, UML, ArchiMate, and C4. Rows are inserted
idempotently via INSERT OR IGNORE; existing DoView-era rows are never touched.

The prompt text itself is defined once in app.seed.creation_prompts and
re-used here — each prompt's id is suffixed -v1 and its content is therefore
frozen. Any future revision lands as a -v2 row in a later migration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.seed.creation_prompts import _EXPANSION_ROWS

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    for row in _EXPANSION_ROWS:
        await db.execute(
            "INSERT OR IGNORE INTO ai_creation_prompts "
            "(id, name, description, layer, notation, diagram_type, "
            "prompt_text, display_order, is_active, created_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 'system')",
            (
                row["id"],
                row["name"],
                row["description"],
                row["layer"],
                row["notation"],
                row["diagram_type"],
                row["prompt_text"],
                row["display_order"],
            ),
        )

    await db.commit()
