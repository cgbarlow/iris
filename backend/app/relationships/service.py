"""Relationship CRUD service with versioning per SPEC-003-A."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def create_relationship(
    db: aiosqlite.Connection,
    *,
    source_entity_id: str,
    target_entity_id: str,
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
        "(id, source_entity_id, target_entity_id, relationship_type, "
        "current_version, created_at, created_by, updated_at) "
        "VALUES (?, ?, ?, ?, 1, ?, ?, ?)",
        (rel_id, source_entity_id, target_entity_id,
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

    return {
        "id": rel_id,
        "source_entity_id": source_entity_id,
        "target_entity_id": target_entity_id,
        "relationship_type": relationship_type,
        "current_version": 1,
        "label": label,
        "description": description,
        "data": data,
        "created_at": now,
        "created_by": created_by,
        "updated_at": now,
        "is_deleted": False,
    }


async def get_relationship(
    db: aiosqlite.Connection,
    rel_id: str,
) -> dict[str, object] | None:
    """Get a relationship with its current version data."""
    cursor = await db.execute(
        "SELECT r.id, r.source_entity_id, r.target_entity_id, "
        "r.relationship_type, r.current_version, "
        "rv.label, rv.description, rv.data, "
        "r.created_at, r.created_by, r.updated_at, r.is_deleted, "
        "sev.name, tev.name "
        "FROM relationships r "
        "JOIN relationship_versions rv ON r.id = rv.relationship_id "
        "AND r.current_version = rv.version "
        "LEFT JOIN entities se ON r.source_entity_id = se.id "
        "AND se.is_deleted = 0 "
        "LEFT JOIN entity_versions sev ON se.id = sev.entity_id "
        "AND se.current_version = sev.version "
        "LEFT JOIN entities te ON r.target_entity_id = te.id "
        "AND te.is_deleted = 0 "
        "LEFT JOIN entity_versions tev ON te.id = tev.entity_id "
        "AND te.current_version = tev.version "
        "WHERE r.id = ? AND r.is_deleted = 0",
        (rel_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    return {
        "id": row[0],
        "source_entity_id": row[1],
        "target_entity_id": row[2],
        "relationship_type": row[3],
        "current_version": row[4],
        "label": row[5],
        "description": row[6],
        "data": json.loads(row[7]) if row[7] else {},
        "created_at": row[8],
        "created_by": row[9],
        "updated_at": row[10],
        "is_deleted": bool(row[11]),
        "source_entity_name": row[12] or "",
        "target_entity_name": row[13] or "",
    }


async def list_relationships(
    db: aiosqlite.Connection,
    *,
    entity_id: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict[str, object]], int]:
    """List relationships, optionally filtered by entity involvement."""
    where_clauses = ["r.is_deleted = 0"]
    params: list[object] = []

    if entity_id:
        where_clauses.append(
            "(r.source_entity_id = ? OR r.target_entity_id = ?)"
        )
        params.extend([entity_id, entity_id])

    where_sql = " AND ".join(where_clauses)

    cursor = await db.execute(
        f"SELECT COUNT(*) FROM relationships r WHERE {where_sql}",  # noqa: S608
        params,
    )
    count_row = await cursor.fetchone()
    total: int = count_row[0]  # type: ignore[index]

    offset = (page - 1) * page_size
    cursor = await db.execute(
        f"SELECT r.id, r.source_entity_id, r.target_entity_id, "  # noqa: S608
        "r.relationship_type, r.current_version, "
        "rv.label, rv.description, rv.data, "
        "r.created_at, r.created_by, r.updated_at, r.is_deleted, "
        "sev.name, tev.name "
        "FROM relationships r "
        "JOIN relationship_versions rv ON r.id = rv.relationship_id "
        "AND r.current_version = rv.version "
        "LEFT JOIN entities se ON r.source_entity_id = se.id "
        "AND se.is_deleted = 0 "
        "LEFT JOIN entity_versions sev ON se.id = sev.entity_id "
        "AND se.current_version = sev.version "
        "LEFT JOIN entities te ON r.target_entity_id = te.id "
        "AND te.is_deleted = 0 "
        "LEFT JOIN entity_versions tev ON te.id = tev.entity_id "
        "AND te.current_version = tev.version "
        f"WHERE {where_sql} "
        "ORDER BY r.updated_at DESC LIMIT ? OFFSET ?",
        [*params, page_size, offset],
    )
    rows = await cursor.fetchall()

    items = [
        {
            "id": r[0],
            "source_entity_id": r[1],
            "target_entity_id": r[2],
            "relationship_type": r[3],
            "current_version": r[4],
            "label": r[5],
            "description": r[6],
            "data": json.loads(r[7]) if r[7] else {},
            "created_at": r[8],
            "created_by": r[9],
            "updated_at": r[10],
            "is_deleted": bool(r[11]),
            "source_entity_name": r[12] or "",
            "target_entity_name": r[13] or "",
        }
        for r in rows
    ]
    return items, total


async def update_relationship(
    db: aiosqlite.Connection,
    rel_id: str,
    *,
    label: str | None,
    description: str | None,
    data: dict[str, object],
    change_summary: str | None,
    updated_by: str,
    expected_version: int,
) -> dict[str, object] | None:
    """Update a relationship with OCC."""
    cursor = await db.execute(
        "SELECT current_version FROM relationships "
        "WHERE id = ? AND is_deleted = 0",
        (rel_id,),
    )
    row = await cursor.fetchone()
    if row is None or row[0] != expected_version:
        return None

    new_version = row[0] + 1
    now = datetime.now(tz=UTC).isoformat()
    data_json = json.dumps(data)

    await db.execute(
        "UPDATE relationships SET current_version = ?, updated_at = ? "
        "WHERE id = ?",
        (new_version, now, rel_id),
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
    db: aiosqlite.Connection,
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
