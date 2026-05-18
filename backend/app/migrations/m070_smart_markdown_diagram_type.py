"""Migration 070: Smart Markdown diagram type (ADR-205, issue #185).

Registers ``smart_markdown`` under the existing ``markdown`` notation
(ADR-137, m044). No new tables — source markdown lives in the diagram's
``data.markdown_source`` JSON; resolved content is synthesised on
read (ADR-187) into ``data.content``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m070_smart_markdown_diagram_type"

_DIAGRAM_TYPE = (
    "smart_markdown",
    "Smart Markdown",
    "Markdown with inline references to Iris entity fields",
    17,
)
_MAPPINGS = [
    # is_default=0 — markdown notation already defaults to text.
    ("smart_markdown", "markdown", 0),
]


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up. Idempotent — INSERT OR IGNORE on both rows."""
    dt_id, dt_name, dt_desc, dt_order = _DIAGRAM_TYPE
    await db.execute(
        "INSERT OR IGNORE INTO diagram_types "
        "(id, name, description, display_order) VALUES (?, ?, ?, ?)",
        (dt_id, dt_name, dt_desc, dt_order),
    )
    for dt_id_, n_id_, is_default in _MAPPINGS:
        await db.execute(
            "INSERT OR IGNORE INTO diagram_type_notations "
            "(diagram_type_id, notation_id, is_default) VALUES (?, ?, ?)",
            (dt_id_, n_id_, is_default),
        )
    await db.commit()
