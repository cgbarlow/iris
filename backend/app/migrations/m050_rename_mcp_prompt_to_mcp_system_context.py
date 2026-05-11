"""Migration 050: rename `mcp_prompt` → `mcp_system_context` on
`collections` and `sets` (ADR-156, SPEC-156-A).

v5.10.0 (ADR-155) shipped the column as `mcp_prompt` and surfaced
its body via the MCP `prompts` channel (slash-command picker). v5.11.0
(ADR-156) repositions it as a **data passthrough** field that flows
through `get_set` / `get_collection` MCP tool responses as scope
context — no slash command. The rename reflects the new purpose.

Idempotent. PRAGMA-checks column existence on both sides of the
rename: only renames if the old name is present and the new name is
absent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m050_rename_mcp_prompt_to_mcp_system_context"


async def _rename_if_needed(db: aiosqlite.Connection, table: str) -> None:
    cursor = await db.execute(f"PRAGMA table_info({table})")
    columns = {row[1] for row in await cursor.fetchall()}
    if "mcp_prompt" in columns and "mcp_system_context" not in columns:
        await db.execute(
            f"ALTER TABLE {table} RENAME COLUMN mcp_prompt TO mcp_system_context",
        )


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up — idempotent column rename on both tables."""
    await _rename_if_needed(db, "collections")
    await _rename_if_needed(db, "sets")
    await db.commit()
