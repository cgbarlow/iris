# ruff: noqa: E501
"""Migration 059: insert ASKING QUESTIONS section into the
mcp-server-instructions-v1 singleton body (ADR-177, SPEC-177-A, v6.1.0).

Issue #133 Phase 1. Promotes the AskUserQuestion convention from a
single sentence buried inside ORIENT-FIRST PROTOCOL step 3 into a
first-class top-level section between ORIENT-FIRST PROTOCOL and
DISCOVERY TOOLS.

Surgical REPLACE() — preserves admin customisations elsewhere in the
body, matches the m057_fix_stale_auth_recovery pattern. Idempotent:
REPLACE is a no-op when the marker substring isn't present (so re-runs
after the section is already inserted are silent).

The canonical body is mirrored in `app/seed/creation_prompts.py` which
re-applies it on every backend startup. This is new behaviour for the
mcp-server-instructions row (m053 only INSERT-OR-IGNORE'd at first
install; m057 patched in place; this phase adopts the
cascade-prompt re-apply-on-startup pattern so future copy edits ship
without a new migration).

The iris-mcp `_FALLBACK_INSTRUCTIONS` is updated in lockstep so
day-one fallback matches the seeded body.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m059_mcp_user_question_rule"


# The closing line of the ORIENT-FIRST PROTOCOL section in the v5.18.0
# seed (m053). The new ASKING QUESTIONS section is inserted directly
# after this line. The replacement is the original line followed by
# two newlines and the new section.
_ORIENT_END_MARKER = (
    "  3. Offer the menu of options the orient sheet specifies, IN "
    "ORDER, VERBATIM. Use AskUserQuestion when the client supports it; "
    "numbered list otherwise. Do not paraphrase, do not silently drop "
    "options."
)

_ASKING_QUESTIONS_SECTION = """\

ASKING QUESTIONS.
Whenever you need the user to choose from a finite set of options, ask via the MCP client's structured user-question tool (AskUserQuestion in Claude Code / Claude Desktop / Cursor). Do not embed multi-option questions in prose. Do not list multiple questions in a single message — one question per turn, wait for the answer, then ask the next. When the client does not expose a user-question tool, fall back to a numbered list with options IN ORDER, VERBATIM (no paraphrasing).
This applies to:
  - the orient menu (already covered in ORIENT-FIRST above),
  - every Stage-0 setup question in a creation cascade,
  - the save-destination chooser,
  - any other choice the model surfaces to the user.
If you ever feel unsure whether a question warrants the tool: it does."""


_REPLACEMENT_TEXT = _ORIENT_END_MARKER + _ASKING_QUESTIONS_SECTION


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up."""
    # No-op gracefully on isolated test fixtures.
    cursor = await db.execute(
        "SELECT name FROM sqlite_master"
        " WHERE type='table' AND name='ai_creation_prompts'",
    )
    if await cursor.fetchone() is None:
        return

    await db.execute(
        "UPDATE ai_creation_prompts"
        " SET prompt_text = REPLACE(prompt_text, ?, ?)"
        " WHERE purpose = 'mcp_server_instructions'",
        (_ORIENT_END_MARKER, _REPLACEMENT_TEXT),
    )
    await db.commit()
