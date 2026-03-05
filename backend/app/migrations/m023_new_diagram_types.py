"""Migration 023: New diagram types and notation mappings (ADR-082).

Adds 6 new diagram types (use_case, state_machine, system_context, container,
motivation, strategy) and 2 quick-win notation mappings (archimate→roadmap,
c4→sequence).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

# ── New diagram types ────────────────────────────────────────────────────────

_NEW_DIAGRAM_TYPES = [
    ("use_case", "Use Case", "User goals and system interactions", 7),
    ("state_machine", "State Machine", "State transitions and lifecycles", 8),
    ("system_context", "System Context", "C4 Level 1 — systems and actors", 9),
    ("container", "Container", "C4 Level 2 — containers within a system", 10),
    ("motivation", "Motivation", "ArchiMate motivation viewpoint", 11),
    ("strategy", "Strategy", "ArchiMate strategy viewpoint", 12),
]

# ── Notation mappings for new types + quick-win additions ────────────────────

_NEW_MAPPINGS = [
    # use_case: simple, uml*
    ("use_case", "simple", 0),
    ("use_case", "uml", 1),
    # state_machine: simple, uml*
    ("state_machine", "simple", 0),
    ("state_machine", "uml", 1),
    # system_context: simple, c4*
    ("system_context", "simple", 0),
    ("system_context", "c4", 1),
    # container: simple, c4*
    ("container", "simple", 0),
    ("container", "c4", 1),
    # motivation: archimate*
    ("motivation", "archimate", 1),
    # strategy: archimate*
    ("strategy", "archimate", 1),
    # Quick-win: add archimate to roadmap (default stays simple)
    ("roadmap", "archimate", 0),
    # Quick-win: add c4 to sequence (default stays uml)
    ("sequence", "c4", 0),
]


async def up(db: aiosqlite.Connection) -> None:
    """Add new diagram types and notation mappings."""
    # 1. Insert new diagram types (idempotent)
    for dt_id, dt_name, dt_desc, dt_order in _NEW_DIAGRAM_TYPES:
        await db.execute(
            "INSERT OR IGNORE INTO diagram_types (id, name, description, display_order) "
            "VALUES (?, ?, ?, ?)",
            (dt_id, dt_name, dt_desc, dt_order),
        )

    # 2. Insert notation mappings (idempotent)
    for dt_id, n_id, is_default in _NEW_MAPPINGS:
        await db.execute(
            "INSERT OR IGNORE INTO diagram_type_notations "
            "(diagram_type_id, notation_id, is_default) VALUES (?, ?, ?)",
            (dt_id, n_id, is_default),
        )

    await db.commit()
