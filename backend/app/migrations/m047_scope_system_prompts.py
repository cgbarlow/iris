"""Migration 047: Scope-level system prompts (ADR-150, SPEC-150-A).

Adds a nullable `system_prompt TEXT` column to `collections` and `sets`
so the owner of a scope can attach domain-specific instructions that
travel with every AI question (Ask Iris discuss / creation; Iris MCP
`ask` tool) that touches the scope.

Inheritance is additive — a Set inherits its parent Collection's
prompt rather than overriding it. Composition is performed at runtime
in `app/ai/scope_prompts.py`; this migration only adds the storage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m047_scope_system_prompts"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up — additive ALTER COLUMNs, idempotent."""
    cursor = await db.execute("PRAGMA table_info(collections)")
    columns = {row[1] for row in await cursor.fetchall()}
    if "system_prompt" not in columns:
        await db.execute("ALTER TABLE collections ADD COLUMN system_prompt TEXT")

    cursor = await db.execute("PRAGMA table_info(sets)")
    columns = {row[1] for row in await cursor.fetchall()}
    if "system_prompt" not in columns:
        await db.execute("ALTER TABLE sets ADD COLUMN system_prompt TEXT")

    await db.commit()
