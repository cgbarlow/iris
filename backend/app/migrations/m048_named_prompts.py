"""Migration 048: Multiple named prompts per scope (ADR-154, SPEC-154-A).

Creates the `prompts` table holding zero-or-more named prompts per
Collection or Set. Named prompts are surfaced via the MCP `prompts`
channel as `set:<uuid>:<name>` / `collection:<uuid>:<name>` (post-ADR-153
naming, no `iris:` prefix). They are picker-invoked only; the scope
`system_prompt` column (m047) continues to auto-apply via the Ask
Iris composition pipeline and is untouched.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m048_named_prompts"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up — additive new table, idempotent."""
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS prompts (
            id           TEXT PRIMARY KEY,
            scope_type   TEXT NOT NULL CHECK (scope_type IN ('collection','set')),
            scope_id     TEXT NOT NULL,
            name         TEXT NOT NULL,
            description  TEXT NOT NULL,
            body         TEXT NOT NULL,
            created_at   TEXT NOT NULL,
            updated_at   TEXT NOT NULL,
            created_by   TEXT,
            UNIQUE (scope_type, scope_id, name)
        )
        """
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_prompts_scope ON prompts(scope_type, scope_id)"
    )
    await db.commit()
