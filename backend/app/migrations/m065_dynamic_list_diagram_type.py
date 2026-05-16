"""Migration 065: Dynamic List diagram type (ADR-186, issue #147).

Registers ``dynamic_list`` under the existing ``markdown`` notation
(ADR-137, m044). No new tables — source config lives in the diagram's
``data.dynamic_source`` JSON; the bullet content is synthesised on
read (ADR-187).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m065_dynamic_list_diagram_type"

_DIAGRAM_TYPE = (
    "dynamic_list",
    "Dynamic List",
    "Auto-generated markdown bullet list",
    16,
)
_MAPPINGS = [
    # is_default=0 — markdown notation already defaults to text.
    ("dynamic_list", "markdown", 0),
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
