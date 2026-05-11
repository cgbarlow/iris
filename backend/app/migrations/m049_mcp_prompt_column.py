"""Migration 049: scope MCP prompt column (ADR-155, SPEC-155-A).

Adds a nullable `mcp_prompt TEXT` column to `collections` and `sets`.
This column powers the scope's MCP `prompts` picker entry
(`set:<uuid>` / `collection:<uuid>`) and is NEVER auto-prepended to
Iris AI server-side composition — the opposite of v5.8.0's
`system_prompt` column (ADR-150), which continues to auto-apply in
Iris AI but is no longer surfaced via the MCP picker.

Strict-split semantics — see ADR-155.

SQLite does not need a timestamp-column fix; SQLite's dynamic typing
accepts ISO datetime strings in TEXT columns. The Supabase mirror
m053 also includes the timestamptz conversion on the v5.9.0 prompts
table.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m049_mcp_prompt_column"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up — additive ALTER COLUMNs, idempotent."""
    cursor = await db.execute("PRAGMA table_info(collections)")
    columns = {row[1] for row in await cursor.fetchall()}
    if "mcp_prompt" not in columns:
        await db.execute("ALTER TABLE collections ADD COLUMN mcp_prompt TEXT")

    cursor = await db.execute("PRAGMA table_info(sets)")
    columns = {row[1] for row in await cursor.fetchall()}
    if "mcp_prompt" not in columns:
        await db.execute("ALTER TABLE sets ADD COLUMN mcp_prompt TEXT")

    await db.commit()
