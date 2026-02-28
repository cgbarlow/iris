"""Entity CRUD service with versioning per SPEC-006-A."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.search.service import index_entity as _index_entity
from app.search.service import remove_entity_index as _remove_entity_index

if TYPE_CHECKING:
    import aiosqlite


async def create_entity(
    db: aiosqlite.Connection,
    *,
    entity_type: str,
    name: str,
    description: str | None,
    data: dict[str, object],
    created_by: str,
) -> dict[str, object]:
    """Create a new entity with initial version."""
    entity_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    data_json = json.dumps(data)

    await db.execute(
        "INSERT INTO entities (id, entity_type, current_version, "
        "created_at, created_by, updated_at) VALUES (?, ?, 1, ?, ?, ?)",
        (entity_id, entity_type, now, created_by, now),
    )
    await db.execute(
        "INSERT INTO entity_versions (entity_id, version, name, description, "
        "data, change_type, created_at, created_by) "
        "VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
        (entity_id, name, description, data_json, now, created_by),
    )
    await db.commit()
    await _index_entity(
        db, entity_id=entity_id, name=name,
        entity_type=entity_type, description=description,
    )
    await db.commit()

    return {
        "id": entity_id,
        "entity_type": entity_type,
        "current_version": 1,
        "name": name,
        "description": description,
        "data": data,
        "created_at": now,
        "created_by": created_by,
        "updated_at": now,
        "is_deleted": False,
    }


async def get_entity(
    db: aiosqlite.Connection,
    entity_id: str,
) -> dict[str, object] | None:
    """Get an entity with its current version data."""
    cursor = await db.execute(
        "SELECT e.id, e.entity_type, e.current_version, "
        "ev.name, ev.description, ev.data, "
        "e.created_at, e.created_by, e.updated_at, e.is_deleted "
        "FROM entities e "
        "JOIN entity_versions ev ON e.id = ev.entity_id "
        "AND e.current_version = ev.version "
        "WHERE e.id = ? AND e.is_deleted = 0",
        (entity_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    return {
        "id": row[0],
        "entity_type": row[1],
        "current_version": row[2],
        "name": row[3],
        "description": row[4],
        "data": json.loads(row[5]) if row[5] else {},
        "created_at": row[6],
        "created_by": row[7],
        "updated_at": row[8],
        "is_deleted": bool(row[9]),
    }


async def list_entities(
    db: aiosqlite.Connection,
    *,
    entity_type: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict[str, object]], int]:
    """List entities with pagination. Returns (items, total_count)."""
    where_clauses = ["e.is_deleted = 0"]
    params: list[object] = []

    if entity_type:
        where_clauses.append("e.entity_type = ?")
        params.append(entity_type)

    where_sql = " AND ".join(where_clauses)

    # Count
    cursor = await db.execute(
        f"SELECT COUNT(*) FROM entities e WHERE {where_sql}",  # noqa: S608
        params,
    )
    count_row = await cursor.fetchone()
    total: int = count_row[0]  # type: ignore[index]

    # Fetch page
    offset = (page - 1) * page_size
    cursor = await db.execute(
        f"SELECT e.id, e.entity_type, e.current_version, "  # noqa: S608
        "ev.name, ev.description, ev.data, "
        "e.created_at, e.created_by, e.updated_at, e.is_deleted "
        "FROM entities e "
        "JOIN entity_versions ev ON e.id = ev.entity_id "
        "AND e.current_version = ev.version "
        f"WHERE {where_sql} "
        "ORDER BY e.updated_at DESC LIMIT ? OFFSET ?",
        [*params, page_size, offset],
    )
    rows = await cursor.fetchall()

    items = [
        {
            "id": r[0],
            "entity_type": r[1],
            "current_version": r[2],
            "name": r[3],
            "description": r[4],
            "data": json.loads(r[5]) if r[5] else {},
            "created_at": r[6],
            "created_by": r[7],
            "updated_at": r[8],
            "is_deleted": bool(r[9]),
        }
        for r in rows
    ]
    return items, total


async def update_entity(
    db: aiosqlite.Connection,
    entity_id: str,
    *,
    name: str,
    description: str | None,
    data: dict[str, object],
    change_summary: str | None,
    updated_by: str,
    expected_version: int,
) -> dict[str, object] | None:
    """Update an entity with optimistic concurrency. Returns None on conflict."""
    # Check current version (OCC)
    cursor = await db.execute(
        "SELECT current_version FROM entities WHERE id = ? AND is_deleted = 0",
        (entity_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    current_version: int = row[0]
    if current_version != expected_version:
        return None

    new_version = current_version + 1
    now = datetime.now(tz=UTC).isoformat()
    data_json = json.dumps(data)

    await db.execute(
        "UPDATE entities SET current_version = ?, updated_at = ? WHERE id = ?",
        (new_version, now, entity_id),
    )
    await db.execute(
        "INSERT INTO entity_versions (entity_id, version, name, description, "
        "data, change_type, change_summary, created_at, created_by) "
        "VALUES (?, ?, ?, ?, ?, 'update', ?, ?, ?)",
        (entity_id, new_version, name, description, data_json,
         change_summary, now, updated_by),
    )
    await db.commit()

    # Re-index for search — need entity_type from the entity row
    type_cursor = await db.execute(
        "SELECT entity_type FROM entities WHERE id = ?", (entity_id,),
    )
    type_row = await type_cursor.fetchone()
    if type_row:
        await _index_entity(
            db, entity_id=entity_id, name=name,
            entity_type=type_row[0], description=description,
        )
        await db.commit()

    return {
        "id": entity_id,
        "current_version": new_version,
        "name": name,
        "description": description,
        "data": data,
        "updated_at": now,
    }


async def rollback_entity(
    db: aiosqlite.Connection,
    entity_id: str,
    *,
    target_version: int,
    rolled_back_by: str,
    expected_version: int,
) -> dict[str, object] | None:
    """Rollback entity to a previous version (creates new version). Returns None on conflict."""
    # Check current version (OCC)
    cursor = await db.execute(
        "SELECT current_version FROM entities WHERE id = ? AND is_deleted = 0",
        (entity_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    current_version: int = row[0]
    if current_version != expected_version:
        return None

    # Get target version data
    cursor = await db.execute(
        "SELECT name, description, data FROM entity_versions "
        "WHERE entity_id = ? AND version = ?",
        (entity_id, target_version),
    )
    target_row = await cursor.fetchone()
    if target_row is None:
        return None

    new_version = current_version + 1
    now = datetime.now(tz=UTC).isoformat()

    await db.execute(
        "UPDATE entities SET current_version = ?, updated_at = ? WHERE id = ?",
        (new_version, now, entity_id),
    )
    await db.execute(
        "INSERT INTO entity_versions (entity_id, version, name, description, "
        "data, change_type, rollback_to, created_at, created_by) "
        "VALUES (?, ?, ?, ?, ?, 'rollback', ?, ?, ?)",
        (entity_id, new_version, target_row[0], target_row[1],
         target_row[2], target_version, now, rolled_back_by),
    )
    await db.commit()

    # Re-index for search after rollback
    type_cursor = await db.execute(
        "SELECT entity_type FROM entities WHERE id = ?", (entity_id,),
    )
    type_row = await type_cursor.fetchone()
    if type_row:
        await _index_entity(
            db, entity_id=entity_id, name=target_row[0],
            entity_type=type_row[0], description=target_row[1],
        )
        await db.commit()

    return {
        "id": entity_id,
        "current_version": new_version,
        "name": target_row[0],
        "description": target_row[1],
        "data": json.loads(target_row[2]) if target_row[2] else {},
        "updated_at": now,
    }


async def soft_delete_entity(
    db: aiosqlite.Connection,
    entity_id: str,
    *,
    deleted_by: str,
    expected_version: int,
) -> bool:
    """Soft-delete an entity. Returns False on conflict or not found."""
    cursor = await db.execute(
        "SELECT current_version FROM entities WHERE id = ? AND is_deleted = 0",
        (entity_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return False

    current_version: int = row[0]
    if current_version != expected_version:
        return False

    new_version = current_version + 1
    now = datetime.now(tz=UTC).isoformat()

    # Get current version data for the delete version record
    cursor = await db.execute(
        "SELECT name, description, data FROM entity_versions "
        "WHERE entity_id = ? AND version = ?",
        (entity_id, current_version),
    )
    ver_row = await cursor.fetchone()

    await db.execute(
        "UPDATE entities SET current_version = ?, updated_at = ?, "
        "is_deleted = 1 WHERE id = ?",
        (new_version, now, entity_id),
    )
    await db.execute(
        "INSERT INTO entity_versions (entity_id, version, name, description, "
        "data, change_type, created_at, created_by) "
        "VALUES (?, ?, ?, ?, ?, 'delete', ?, ?)",
        (entity_id, new_version, ver_row[0], ver_row[1],
         ver_row[2], now, deleted_by),
    )
    await db.commit()
    await _remove_entity_index(db, entity_id)
    await db.commit()
    return True


async def get_entity_versions(
    db: aiosqlite.Connection,
    entity_id: str,
) -> list[dict[str, object]]:
    """Get all versions of an entity."""
    cursor = await db.execute(
        "SELECT entity_id, version, name, description, data, "
        "change_type, change_summary, rollback_to, "
        "created_at, created_by "
        "FROM entity_versions WHERE entity_id = ? "
        "ORDER BY version DESC",
        (entity_id,),
    )
    rows = await cursor.fetchall()
    return [
        {
            "entity_id": r[0],
            "version": r[1],
            "name": r[2],
            "description": r[3],
            "data": json.loads(r[4]) if r[4] else {},
            "change_type": r[5],
            "change_summary": r[6],
            "rollback_to": r[7],
            "created_at": r[8],
            "created_by": r[9],
        }
        for r in rows
    ]


async def get_entity_version(
    db: aiosqlite.Connection,
    entity_id: str,
    version: int,
) -> dict[str, object] | None:
    """Get a specific version of an entity."""
    cursor = await db.execute(
        "SELECT entity_id, version, name, description, data, "
        "change_type, change_summary, rollback_to, "
        "created_at, created_by "
        "FROM entity_versions WHERE entity_id = ? AND version = ?",
        (entity_id, version),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    return {
        "entity_id": row[0],
        "version": row[1],
        "name": row[2],
        "description": row[3],
        "data": json.loads(row[4]) if row[4] else {},
        "change_type": row[5],
        "change_summary": row[6],
        "rollback_to": row[7],
        "created_at": row[8],
        "created_by": row[9],
    }
