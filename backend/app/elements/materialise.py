"""Shared element/relationship materialisation (ADR-100).

Provides low-level INSERT helpers that create element + version and
relationship + version records without committing.  Callers control
transaction boundaries.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


async def materialise_element(
    db: DatabasePort,
    *,
    element_id: str,
    element_type: str,
    name: str,
    description: str | None,
    set_id: str,
    notation: str,
    created_by: str,
    now: str,
) -> None:
    """Insert element + initial version records (caller commits)."""
    await db.execute(
        "INSERT INTO elements (id, element_type, set_id, current_version, "
        "created_at, created_by, updated_at, notation) VALUES (?, ?, ?, 1, ?, ?, ?, ?)",
        (element_id, element_type, set_id, now, created_by, now, notation),
    )
    await db.execute(
        "INSERT INTO element_versions (element_id, version, name, description, "
        "data, change_type, created_at, created_by) "
        "VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
        (element_id, name, description, json.dumps({}), now, created_by),
    )


async def materialise_relationship(
    db: DatabasePort,
    *,
    rel_id: str,
    source_element_id: str,
    target_element_id: str,
    relationship_type: str,
    label: str,
    description: str,
    created_by: str,
    now: str,
) -> None:
    """Insert relationship + initial version records (caller commits)."""
    await db.execute(
        "INSERT INTO relationships (id, source_element_id, target_element_id, "
        "relationship_type, current_version, created_at, created_by, updated_at) "
        "VALUES (?, ?, ?, ?, 1, ?, ?, ?)",
        (rel_id, source_element_id, target_element_id, relationship_type,
         now, created_by, now),
    )
    await db.execute(
        "INSERT INTO relationship_versions (relationship_id, version, label, "
        "description, data, change_type, created_at, created_by) "
        "VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
        (rel_id, label, description, json.dumps({}), now, created_by),
    )
