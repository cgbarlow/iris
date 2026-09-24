"""Relationship CRUD service with versioning per SPEC-003-A.

Handles element-to-element relationships.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import aiosqlite
    from app.db.adapter import DatabasePort

# ADR-249: UML role names live in the relationship's ``data`` under the keys
# the Sparx importer writes (import_sparx/service.py) and the canvas renders
# on edges. Agent surfaces (MCP / CLI / batch REST) take ``source_role`` /
# ``target_role`` and map them here so every write path stores roles the same
# way.
SOURCE_ROLE_KEY = "sourceRole"
TARGET_ROLE_KEY = "targetRole"


class RelationshipValidationError(ValueError):
    """A proposed relationship is not allowed on the agent write path
    (ADR-249): self-referencing, cross-set, or an endpoint not found."""


def apply_role_fields(
    data: dict[str, object],
    *,
    source_role: str | None,
    target_role: str | None,
) -> dict[str, object]:
    """Return a copy of ``data`` with role names merged in (ADR-249).

    ``None`` leaves the key as ``data`` has it; ``""`` removes it; any other
    string sets it (an explicit role wins over a stale ``data`` key).
    """
    merged = dict(data)
    for key, value in ((SOURCE_ROLE_KEY, source_role), (TARGET_ROLE_KEY, target_role)):
        if value is None:
            continue
        if value == "":
            merged.pop(key, None)
        else:
            merged[key] = value
    return merged


def _role(data: dict[str, object], key: str) -> str | None:
    value = data.get(key)
    return value if isinstance(value, str) and value else None


def _with_roles(rel: dict[str, object]) -> dict[str, object]:
    """Add the derived ``source_role`` / ``target_role`` fields (ADR-249)."""
    data = rel.get("data")
    data = data if isinstance(data, dict) else {}
    rel["source_role"] = _role(data, SOURCE_ROLE_KEY)
    rel["target_role"] = _role(data, TARGET_ROLE_KEY)
    return rel


async def validate_new_relationship(
    db: DatabasePort,
    *,
    source_element_id: str,
    target_element_id: str,
) -> None:
    """Reject self-referencing and cross-set relationships (ADR-249).

    Used by the agent-facing batch create path only. It is deliberately
    NOT called from ``create_relationship`` itself: the canvas's self-loop
    edges, the Sparx importer's reflexive associations and diagram-edge
    auto-create all go through that function and legitimately produce
    reflexive relationships (UML permits them).
    """
    if source_element_id == target_element_id:
        raise RelationshipValidationError(
            "self-referencing relationships are not allowed "
            "(source_element_id equals target_element_id)",
        )
    set_ids: dict[str, object] = {}
    for end, element_id in (
        ("source", source_element_id), ("target", target_element_id),
    ):
        cursor = await db.execute(
            "SELECT set_id FROM elements WHERE id = ? AND is_deleted = 0",
            (element_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            raise RelationshipValidationError(
                f"{end} element {element_id} not found",
            )
        set_ids[end] = row[0]
    if set_ids["source"] != set_ids["target"]:
        raise RelationshipValidationError(
            f"cross-set relationships are not allowed: source element "
            f"{source_element_id} is in set {set_ids['source']}, target "
            f"element {target_element_id} is in set {set_ids['target']}",
        )


async def create_relationship(
    db: DatabasePort,
    *,
    source_element_id: str,
    target_element_id: str,
    relationship_type: str,
    label: str | None,
    description: str | None,
    data: dict[str, object],
    created_by: str,
) -> dict[str, object]:
    """Create a new relationship with initial version."""
    rel_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    data_json = json.dumps(data)

    await db.execute(
        "INSERT INTO relationships "
        "(id, source_element_id, target_element_id, relationship_type, "
        "current_version, created_at, created_by, updated_at) "
        "VALUES (?, ?, ?, ?, 1, ?, ?, ?)",
        (rel_id, source_element_id, target_element_id,
         relationship_type, now, created_by, now),
    )
    await db.execute(
        "INSERT INTO relationship_versions "
        "(relationship_id, version, label, description, data, "
        "change_type, created_at, created_by) "
        "VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
        (rel_id, label, description, data_json, now, created_by),
    )
    await db.commit()

    return _with_roles({
        "id": rel_id,
        "source_element_id": source_element_id,
        "target_element_id": target_element_id,
        "relationship_type": relationship_type,
        "current_version": 1,
        "label": label,
        "description": description,
        "data": data,
        "created_at": now,
        "created_by": created_by,
        "updated_at": now,
        "is_deleted": False,
    })


_SELECT_RELATIONSHIP = (
    "SELECT r.id, r.source_element_id, r.target_element_id, "
    "r.relationship_type, r.current_version, "
    "rv.label, rv.description, rv.data, "
    "r.created_at, r.created_by, r.updated_at, r.is_deleted, "
    "sev.name, tev.name "
    "FROM relationships r "
    "JOIN relationship_versions rv ON r.id = rv.relationship_id "
    "AND r.current_version = rv.version "
    "LEFT JOIN elements se ON r.source_element_id = se.id "
    "AND se.is_deleted = 0 "
    "LEFT JOIN element_versions sev ON se.id = sev.element_id "
    "AND se.current_version = sev.version "
    "LEFT JOIN elements te ON r.target_element_id = te.id "
    "AND te.is_deleted = 0 "
    "LEFT JOIN element_versions tev ON te.id = tev.element_id "
    "AND te.current_version = tev.version "
)


def _row_to_relationship(r: Any) -> dict[str, object]:
    """Map a ``_SELECT_RELATIONSHIP`` row, read positionally (protocol §15)."""
    return _with_roles({
        "id": r[0],
        "source_element_id": r[1],
        "target_element_id": r[2],
        "relationship_type": r[3],
        "current_version": r[4],
        "label": r[5],
        "description": r[6],
        "data": json.loads(r[7]) if r[7] else {},
        "created_at": r[8],
        "created_by": r[9],
        "updated_at": r[10],
        "is_deleted": bool(r[11]),
        "source_element_name": r[12] or "",
        "target_element_name": r[13] or "",
    })


async def get_relationship(
    db: DatabasePort,
    rel_id: str,
) -> dict[str, object] | None:
    """Get a relationship with its current version data."""
    cursor = await db.execute(
        _SELECT_RELATIONSHIP + "WHERE r.id = ? AND r.is_deleted = 0",
        (rel_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return _row_to_relationship(row)


async def list_relationships(
    db: DatabasePort,
    *,
    element_id: str | None = None,
    set_id: str | None = None,
    relationship_type: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict[str, object]], int]:
    """List relationships; the filters AND together.

    - ``element_id``: the element is the source OR the target.
    - ``set_id`` (ADR-249): the source OR the target element is in the set,
      so a pre-existing cross-set relationship is visible from both sets.
    - ``relationship_type`` (ADR-249): exact match.
    """
    where_clauses = ["r.is_deleted = 0"]
    params: list[object] = []

    if element_id:
        where_clauses.append(
            "(r.source_element_id = ? OR r.target_element_id = ?)"
        )
        params.extend([element_id, element_id])
    if set_id:
        where_clauses.append(
            "(r.source_element_id IN (SELECT id FROM elements WHERE set_id = ?) "
            "OR r.target_element_id IN (SELECT id FROM elements WHERE set_id = ?))"
        )
        params.extend([set_id, set_id])
    if relationship_type:
        where_clauses.append("r.relationship_type = ?")
        params.append(relationship_type)

    where_sql = " AND ".join(where_clauses)

    cursor = await db.execute(
        f"SELECT COUNT(*) FROM relationships r WHERE {where_sql}",  # noqa: S608
        params,
    )
    count_row = await cursor.fetchone()
    total: int = count_row[0]  # type: ignore[index]

    offset = (page - 1) * page_size
    cursor = await db.execute(
        _SELECT_RELATIONSHIP
        + f"WHERE {where_sql} "
        "ORDER BY r.updated_at DESC, r.id LIMIT ? OFFSET ?",
        [*params, page_size, offset],
    )
    rows = await cursor.fetchall()
    return [_row_to_relationship(r) for r in rows], total


async def update_relationship(
    db: DatabasePort,
    rel_id: str,
    *,
    label: str | None,
    description: str | None,
    data: dict[str, object],
    change_summary: str | None,
    updated_by: str,
    expected_version: int,
    relationship_type: str | None = None,
) -> dict[str, object] | None:
    """Update a relationship with OCC.

    ADR-249: ``relationship_type`` (``None`` = keep) lives on the
    ``relationships`` row, which ``relationship_versions`` doesn't snapshot,
    so a type change is recorded in the new version's ``change_summary``
    (``relationship_type: old -> new``) when the caller doesn't supply one.
    """
    cursor = await db.execute(
        "SELECT current_version, relationship_type FROM relationships "
        "WHERE id = ? AND is_deleted = 0",
        (rel_id,),
    )
    row = await cursor.fetchone()
    if row is None or row[0] != expected_version:
        return None

    new_version = row[0] + 1
    now = datetime.now(tz=UTC).isoformat()
    data_json = json.dumps(data)
    new_type = relationship_type or row[1]
    if new_type != row[1] and change_summary is None:
        change_summary = f"relationship_type: {row[1]} -> {new_type}"

    await db.execute(
        "UPDATE relationships SET current_version = ?, updated_at = ?, "
        "relationship_type = ? WHERE id = ?",
        (new_version, now, new_type, rel_id),
    )
    await db.execute(
        "INSERT INTO relationship_versions "
        "(relationship_id, version, label, description, data, "
        "change_type, change_summary, created_at, created_by) "
        "VALUES (?, ?, ?, ?, ?, 'update', ?, ?, ?)",
        (rel_id, new_version, label, description, data_json,
         change_summary, now, updated_by),
    )
    await db.commit()
    return {"current_version": new_version, "updated_at": now}


async def soft_delete_relationship(
    db: DatabasePort,
    rel_id: str,
    *,
    deleted_by: str,
    expected_version: int,
) -> bool:
    """Soft-delete a relationship."""
    cursor = await db.execute(
        "SELECT current_version FROM relationships "
        "WHERE id = ? AND is_deleted = 0",
        (rel_id,),
    )
    row = await cursor.fetchone()
    if row is None or row[0] != expected_version:
        return False

    new_version = row[0] + 1
    now = datetime.now(tz=UTC).isoformat()

    cursor = await db.execute(
        "SELECT label, description, data FROM relationship_versions "
        "WHERE relationship_id = ? AND version = ?",
        (rel_id, row[0]),
    )
    ver_row = await cursor.fetchone()

    await db.execute(
        "UPDATE relationships SET current_version = ?, updated_at = ?, "
        "is_deleted = 1 WHERE id = ?",
        (new_version, now, rel_id),
    )
    await db.execute(
        "INSERT INTO relationship_versions "
        "(relationship_id, version, label, description, data, "
        "change_type, created_at, created_by) "
        "VALUES (?, ?, ?, ?, ?, 'delete', ?, ?)",
        (rel_id, new_version, ver_row[0], ver_row[1],
         ver_row[2], now, deleted_by),
    )
    await db.commit()
    return True
