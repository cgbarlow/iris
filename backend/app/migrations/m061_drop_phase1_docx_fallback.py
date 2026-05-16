# ruff: noqa: E501, RUF001
"""Migration 061: drop Phase-1 docx/pdf fallback from cascade destination
prompt (ADR-179, SPEC-179-A, v6.2.0).

Issue #133 Phase 2. The destination chooser prompt
`creation-cascade-destination-v1` shipped in v6.1.0 with a Phase-1
fallback paragraph that explained docx/pdf rendering wasn't yet
available. Phase 2 ships the renderer + artefact store, so the
fallback is now obsolete.

Surgical REPLACE() — leaves the cross-set move fallback in place
(move tools ship Phase 3 v6.3.0). Idempotent: REPLACE is a no-op
when the marker substring isn't present.

The seed file `backend/app/seed/creation_prompts.py` is updated in
lockstep — the canonical body of CASCADE_DESTINATION_PROMPT has the
docx/pdf fallback removed and replaced with renderer-call guidance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m061_drop_phase1_docx_fallback"


# The docx/pdf fallback paragraph block as shipped in v6.1.0 (m058,
# CASCADE_DESTINATION_PROMPT body). Replaced with renderer-call
# guidance below.
_PHASE1_DOCX_FALLBACK = """- If the user picks "Chat with downloadable artefacts" and selects
  docx or pdf at Q-Dest3, respond: "Docx and PDF generation ships in
  v6.2.0 (Phase 2 of issue #133). For now I can produce a markdown
  artefact in the chat and create the Iris bundle if you'd like."
  Then offer AskUserQuestion with options "Yes, markdown + Iris save",
  "Just the Iris save", "Cancel and wait for v6.2.0"."""

_RENDERER_CALL_GUIDANCE = """- When the user picks "Chat with downloadable artefacts" and selects
  one or more formats at Q-Dest3, call the MCP `render_markdown`
  tool once per selected format (markdown / docx / pdf). Each call
  returns `{artefact_id, web_url, mime_type, filename}` — present the
  `web_url` to the user as a clickable download link. For "Both"
  (Iris + artefacts), also create the Iris bundle via the
  destination-specific `create_*` tools."""


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
        (_PHASE1_DOCX_FALLBACK, _RENDERER_CALL_GUIDANCE),
    )
    await db.commit()
