"""Migration 053: seed the MCP server-instructions singleton row
(ADR-163, SPEC-163-A, v5.18.0).

Inserts one row into `ai_creation_prompts` with the new
`purpose='mcp_server_instructions'` discriminator value. iris-mcp
fetches this row's body at startup via `GET /api/ai/server-instructions`
and passes it to the MCP SDK `Server(instructions=...)` constructor.
Loaded by every connected MCP client (Claude Desktop, Claude Code,
Cursor, …) on every session.

Singleton at `layer='base'`, `notation=NULL`, `diagram_type=NULL`.
Idempotent (INSERT OR IGNORE on id).

The body is the canonical orient-first protocol + discovery catalogue
+ workflow pointers + auth recovery. Source: docs/prompts/mcp-server-instructions.md
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m053_mcp_server_instructions_seed"


_SEED_BODY = """\
You are connected to Iris (an architectural-modelling tool that exposes Collections, Sets, Packages, Diagrams, Elements, and the relationships between them via this MCP server).

ORIENT-FIRST PROTOCOL.
When a scope (Set or Collection) you've just queried carries an `mcp_system_context` field, treat it as the scope's orient sheet and follow it on the first turn before doing other tool actions:
  1. Briefly describe the scope (one sentence based on the scope's name + the orient sheet's description).
  2. If the orient sheet names a structural-overview call (e.g. iris_package_hierarchy for a Set with packages), make that call and surface the contents.
  3. Offer the menu of options the orient sheet specifies, IN ORDER, VERBATIM. Use AskUserQuestion when the client supports it; numbered list otherwise. Do not paraphrase, do not silently drop options.

DISCOVERY TOOLS.
  list_collections / list_sets / list_packages — structural
  list_notations / list_diagram_types — what's authorable
  list_response_format_types(purpose='response_format'|'creation_format') — what output shapes and what drafting cascades exist
  iris_package_hierarchy(set_id=...) — full tree in one call

WORKFLOW GUIDANCE.
Each tool's description carries its own workflow. For diagram creation, see `create_diagram` (it explains the full discover → fetch creation cascade → guided conversation → confirm destination → save flow). For authentication, see `iris_authenticate`.

AUTH RECOVERY.
Write tools that return error="auth_required" can be unblocked by the iris_authenticate flow — never tell the user to restart their MCP client.
"""


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up."""
    # The `ai_creation_prompts` table is created by m028 / m040; if it
    # doesn't exist yet (test fixture isolation), skip — the seed makes
    # no sense without the table.
    cursor = await db.execute(
        "SELECT name FROM sqlite_master"
        " WHERE type='table' AND name='ai_creation_prompts'",
    )
    if await cursor.fetchone() is None:
        return

    await db.execute(
        "INSERT OR IGNORE INTO ai_creation_prompts "
        "(id, name, description, purpose, layer, notation, diagram_type, "
        "prompt_text, display_order, is_active) "
        "VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, 0, 1)",
        (
            "mcp-server-instructions-v1",
            "MCP Server Instructions",
            (
                "Universal orient-first protocol + discovery catalogue "
                "surfaced by iris-mcp via the MCP server `instructions` "
                "field (ADR-163, v5.18.0). One singleton row at layer=base."
            ),
            "mcp_server_instructions",
            "base",
            _SEED_BODY,
        ),
    )
    await db.commit()
