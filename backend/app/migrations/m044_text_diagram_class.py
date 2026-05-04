"""Migration 044: Text diagram subclass + Markdown notation (ADR-137).

Adds 'markdown' notation and 'text' diagram type to the registry. Text
is a Diagram subclass keyed on (diagram_type='text', notation='markdown')
— no new tables required; markdown source lives in diagrams.data.content.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


_NOTATION = ("markdown", "Markdown", "Markdown text documents (Text diagram subclass)", 6)
_DIAGRAM_TYPE = ("text", "Text Document", "Markdown-backed text document with TOC navigation", 15)
_MAPPINGS = [
    ("text", "markdown", 1),  # markdown is text's default and only canonical notation
]

_AI_PROMPT = (
    "Text diagrams hold structured markdown content rather than a graph canvas. "
    "Use standard markdown for headings (#, ##, ###), lists, code fences, and links. "
    "To link to other Iris models from inside the markdown, use the iris:// URL scheme: "
    "[Some Diagram Name](iris://diagram/<id>) or [Some Element](iris://element/<id>). "
    "These render as in-app navigation — clicking takes the reader to the target. "
    "Headings drive the TOC drawer; sub-headings auto-indent by depth. "
    "Output the document as a single string assigned to data.content. "
    "Do NOT output canvas nodes/edges — text diagrams have no graph."
)


async def up(db: aiosqlite.Connection) -> None:
    """Insert markdown notation, text diagram type, mapping, and AI prompt."""
    now = datetime.now(tz=UTC).isoformat()

    n_id, n_name, n_desc, n_order = _NOTATION
    await db.execute(
        "INSERT OR IGNORE INTO notations (id, name, description, display_order) VALUES (?, ?, ?, ?)",
        (n_id, n_name, n_desc, n_order),
    )

    dt_id, dt_name, dt_desc, dt_order = _DIAGRAM_TYPE
    await db.execute(
        "INSERT OR IGNORE INTO diagram_types (id, name, description, display_order) VALUES (?, ?, ?, ?)",
        (dt_id, dt_name, dt_desc, dt_order),
    )

    for dt_id_, n_id_, is_default in _MAPPINGS:
        await db.execute(
            "INSERT OR IGNORE INTO diagram_type_notations (diagram_type_id, notation_id, is_default) VALUES (?, ?, ?)",
            (dt_id_, n_id_, is_default),
        )

    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='ai_creation_prompts'"
    )
    if await cursor.fetchone():
        await db.execute(
            "INSERT OR REPLACE INTO ai_creation_prompts "
            "(id, name, description, layer, notation, diagram_type, prompt_text, "
            " display_order, is_active, created_by, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "markdown-notation",
                "Markdown Text Prompt",
                "Guidance for generating markdown content for Text diagrams",
                "notation",
                "markdown",
                None,
                _AI_PROMPT,
                100,
                1,
                "system",
                now,
                now,
            ),
        )

    await db.commit()
