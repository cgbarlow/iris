"""Migration 055: fix the orient-protocol tool name in the live
`mcp_server_instructions` singleton row (issue #115, v6.0.1).

The canonical content seeded by m053 referenced the structural-
overview tool as `iris_package_hierarchy`, but the actual MCP-
registered tool name is `package_hierarchy`. claude.ai's stricter
v6-era tool-loading didn't translate the wrong name; the orient
flow lost its TOC step entirely.

This migration is surgical: it replaces the substring
`iris_package_hierarchy` with `package_hierarchy` wherever it appears
in the singleton's `prompt_text`. Admin customisations elsewhere in
the body are preserved (REPLACE is a no-op when the substring isn't
present).

Idempotent — running twice yields the same result. Safe to re-run
after admin edits.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m055_fix_orient_protocol_tool_name"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up."""
    # The table may not exist in isolated test fixtures; guard.
    cursor = await db.execute(
        "SELECT name FROM sqlite_master"
        " WHERE type='table' AND name='ai_creation_prompts'",
    )
    if await cursor.fetchone() is None:
        return

    await db.execute(
        "UPDATE ai_creation_prompts"
        " SET prompt_text = REPLACE(prompt_text,"
        "                          'iris_package_hierarchy',"
        "                          'package_hierarchy')"
        " WHERE purpose = 'mcp_server_instructions'",
    )
    await db.commit()
