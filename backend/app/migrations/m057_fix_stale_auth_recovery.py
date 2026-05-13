"""Migration 057: rewrite the AUTH RECOVERY + WORKFLOW GUIDANCE
sections of the live `mcp_server_instructions` singleton row to
remove references to the v6.0.0-removed `iris_authenticate` tool
(issue #115 follow-up, v6.0.3).

The v5.18.0 seed (m053) included two sentences referencing the
v5.15.0 `iris_authenticate` flow. v6.0.0 (ADR-164) removed that
tool but didn't update the seed body. Live deployments seeded with
v5.18.0 carried the stale references through v6.0.0 → v6.0.2 even
after m055 fixed the unrelated `iris_package_hierarchy` typo.

This migration replaces the two specific stale strings with their
v6.0.0 canonical replacements. Surgical — preserves any admin
customisations elsewhere in the body. Idempotent (REPLACE is a
no-op when the substring isn't found).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m057_fix_stale_auth_recovery"


# The two stale strings from the v5.18.0 / v6.0.0 / v6.0.1 / v6.0.2
# seed body, with their v6.0.0 canonical replacements. Keep these
# byte-for-byte aligned with the m053 seed body.

_STALE_WORKFLOW_SENTENCE = (
    "Each tool's description carries its own workflow. For diagram "
    "creation, see `create_diagram` (it explains the full discover "
    "→ fetch creation cascade → guided conversation → confirm "
    "destination → save flow). For authentication, see `iris_authenticate`."
)
_NEW_WORKFLOW_SENTENCE = (
    "Each tool's description carries its own workflow. For diagram "
    "creation, see `create_diagram` (it explains the full discover "
    "→ fetch creation cascade → guided conversation → confirm "
    "destination → save flow)."
)

_STALE_AUTH_PARAGRAPH = (
    "Write tools that return error=\"auth_required\" can be unblocked "
    "by the iris_authenticate flow — never tell the user to restart "
    "their MCP client."
)
_NEW_AUTH_PARAGRAPH = (
    "If a write tool returns error=\"auth_required\" (HTTP transport), "
    "advise the user to configure OAuth in their MCP client's "
    "connector settings (e.g. claude.ai → Connectors → Iris → "
    "Configure → enable OAuth). The browser opens a consent screen, "
    "the user signs in to Iris, and writes work from then on. Don't "
    "call any auth-related tool yourself — the OAuth handshake is "
    "between the MCP client and Iris, not via tool calls."
)


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up."""
    cursor = await db.execute(
        "SELECT name FROM sqlite_master"
        " WHERE type='table' AND name='ai_creation_prompts'",
    )
    if await cursor.fetchone() is None:
        return

    await db.execute(
        "UPDATE ai_creation_prompts"
        " SET prompt_text = REPLACE("
        "   REPLACE(prompt_text, ?, ?),"
        "   ?, ?)"
        " WHERE purpose = 'mcp_server_instructions'",
        (
            _STALE_WORKFLOW_SENTENCE, _NEW_WORKFLOW_SENTENCE,
            _STALE_AUTH_PARAGRAPH, _NEW_AUTH_PARAGRAPH,
        ),
    )
    await db.commit()
