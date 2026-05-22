"""Migration 078: register the `aggregation_list` diagram type (ADR-213).

Synth-on-read diagram type under the `markdown` notation. Storage is
minimal config (`data.source_diagram_id` + `data.profile_id`); the
engine fills `data.content` at GET time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m078_aggregation_list_diagram_type"

_DIAGRAM_TYPE = (
    "aggregation_list",
    "Aggregation list",
    "Synth-on-read aggregation of a source smart-markdown diagram",
    99,
)
_MAPPINGS = [
    ("aggregation_list", "markdown", 0),  # not default for markdown
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
