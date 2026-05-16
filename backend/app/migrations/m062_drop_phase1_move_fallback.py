# ruff: noqa: E501, RUF001
"""Migration 062: drop Phase-1 cross-set move fallback from cascade
destination prompt (ADR-178, SPEC-178-A, v6.3.0).

Issue #133 Phase 3. The destination chooser prompt
`creation-cascade-destination-v1` carried a fallback paragraph
explaining that cross-set saves required a follow-up `move_*` tool
call that didn't exist yet. Phase 3 ships `move_diagram` /
`move_package` / `move_set`, so the fallback is now obsolete.

Surgical REPLACE() — idempotent (no-op on subsequent runs and on
deploys that never had the v6.1.0 fallback).

The seed file `backend/app/seed/creation_prompts.py` is updated in
lockstep — the canonical CASCADE_DESTINATION_PROMPT body has the
move fallback replaced with concrete tool-call guidance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m062_drop_phase1_move_fallback"


_PHASE1_MOVE_FALLBACK = """- If the user picks "Somewhere else" or "Browse" at Q-Dest2 and the
  chosen destination differs from the current set, respond: "I can
  draft the bundle and save it into the current set now, then move it
  to your chosen destination after v6.3.0 ships move_* tools. Or I
  can describe what I'd save without actually saving, and you can
  re-run after v6.3.0." Then offer AskUserQuestion with these two
  fallbacks."""

_MOVE_TOOL_GUIDANCE = """- When the user picks "Somewhere else" or "Browse" at Q-Dest2 and the
  chosen destination differs from the current set: if the destination
  is an EXISTING set, save the bundle into the current set and then
  call `move_diagram` / `move_package` to relocate; if the destination
  is a NEW set under a different collection, call `create_set` first
  (in the target collection) and save the bundle directly into the
  newly-created set. Move tools cycle-check and are scope-limited to
  in-set re-parenting; cross-set moves require a `create_set` +
  re-save round trip."""


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
        " SET prompt_text = REPLACE(prompt_text, ?, ?)"
        " WHERE id = 'creation-cascade-destination-v1'",
        (_PHASE1_MOVE_FALLBACK, _MOVE_TOOL_GUIDANCE),
    )
    await db.commit()
