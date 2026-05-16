# ruff: noqa: E501
"""Migration 063: backstop creation_format pointer to response_format
for (markdown, doview_analysis) — v6.6.2 regression fix.

Issue #133 Phase 1 UAT (banana monoculture macroeconomics doview
analysis) surfaced a regression that crept in at v6.0.0 (ADR-164):
removing `save_doview_analysis` left the doview_analysis flow
relying on `create_diagram`, but the `_CREATION_FLOW_PREAMBLE` in
mcp/src/iris_mcp/tools.py only directs the model to fetch
`purpose='creation_format'`. The response_format rules (3-section
structure, opening sentence, outcomes-theory framing, tool URLs,
handbook reference) for (markdown, doview_analysis) live only on the
response_format side — the model never fetches them when creating
via the cascade.

This migration adds a small creation_format pointer row at
(layer='diagram_type', diagram_type='doview_analysis') so that any
model fetching the creation_format cascade for doview_analysis sees
an explicit instruction to also fetch and apply the response_format
rules. Single source of truth for the actual rules stays on the
response_format side (m051) per protocols §13 DRY.

Companion change: mcp/src/iris_mcp/tools.py
`_CREATION_FLOW_PREAMBLE` step 2a explicitly tells the model the same.

Idempotent (INSERT OR IGNORE on id).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m063_doview_analysis_creation_format_pointer"


_BODY = """\
## CRITICAL: doview_analysis output structure rules

This diagram's markdown content (`data.content`) MUST follow the
output-structure rules defined in the corresponding response_format
cascade. Those rules are the single source of truth for the
doview_analysis output shape (required opening sentence, three
standalone sections — Summary / Full / Diagrams — outcomes-theory
framing, outcomes-system definition, tool URLs, full handbook
reference at the end).

Before composing the markdown body, fetch and apply:

  get_response_prompt(
    notation='markdown',
    diagram_type='doview_analysis',
    purpose='response_format'
  )

The body returned by that call contains the full set of rules. The
markdown you generate for `data.content` must comply with every one.
Without this fetch, the doview_analysis you produce will not match
the expected output structure and will fail content review.

This pointer exists because the creation_format cascade and
response_format cascade are separate code paths (purpose-discriminated
since ADR-157 / v5.12.0). Cascade-driven creation needs to know that
for (markdown, doview_analysis) the content rules live on the OTHER
purpose. Single source of truth (response_format) preserved; this row
is a pointer, not duplicated content.
"""


_NEW_ROW = {
    "id": "creation-format-doview-analysis-pointer-v1",
    "name": "DoView Analysis — response_format pointer (creation cascade)",
    "description": "Backstop instruction telling the model to fetch and apply the response_format rules when creating a (markdown, doview_analysis) via the creation cascade. Single source of truth for the actual rules stays on the response_format side per DRY. ADR-157 + ADR-180 follow-up, v6.6.2.",
    "purpose": "creation_format",
    "layer": "diagram_type",
    "notation": None,
    "diagram_type": "doview_analysis",
    "prompt_text": _BODY,
    "display_order": 0,
}


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up."""
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
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
        (
            _NEW_ROW["id"],
            _NEW_ROW["name"],
            _NEW_ROW["description"],
            _NEW_ROW["purpose"],
            _NEW_ROW["layer"],
            _NEW_ROW["notation"],
            _NEW_ROW["diagram_type"],
            _NEW_ROW["prompt_text"],
            _NEW_ROW["display_order"],
        ),
    )
    await db.commit()
