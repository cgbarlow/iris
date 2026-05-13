"""Migration 056: fix the orient-protocol tool name in per-scope
`mcp_system_context` fields on sets and collections (issue #115
follow-up, v6.0.2).

v6.0.1 (m055/m059) fixed the server-wide `mcp_server_instructions`
singleton, but the per-scope `mcp_system_context` on the Outcomes
Theory Book set (and any other authored scope) was pasted in the
v5.18.0 / v6.0.0 era when the canonical doc still said
`iris_package_hierarchy`. The live scope content remained stale —
search results still surface the wrong tool name to MCP clients,
and Claude can't load the structural-overview tool with that name.

This migration is surgical: REPLACE() the wrong substring with the
right one in `sets.mcp_system_context` AND `collections.mcp_system_context`
wherever it appears. Admin customisations elsewhere in the body
are preserved (REPLACE is a no-op when the substring isn't present).

Idempotent — running twice yields the same result.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m056_fix_scope_context_tool_name"


async def _fix(db: aiosqlite.Connection, table: str) -> None:
    """REPLACE the wrong tool name in `<table>.mcp_system_context`
    rows. No-op if the table or column doesn't exist (test-fixture
    isolation)."""
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    )
    if await cursor.fetchone() is None:
        return

    cursor = await db.execute(f"PRAGMA table_info({table})")
    columns = {row[1] for row in await cursor.fetchall()}
    if "mcp_system_context" not in columns:
        return

    await db.execute(
        f"UPDATE {table}"
        " SET mcp_system_context = REPLACE(mcp_system_context,"
        "                                  'iris_package_hierarchy',"
        "                                  'package_hierarchy')"
        " WHERE mcp_system_context IS NOT NULL",
    )


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up — idempotent surgical REPLACE on both tables."""
    await _fix(db, "sets")
    await _fix(db, "collections")
    await db.commit()
