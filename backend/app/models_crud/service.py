"""Model CRUD service with versioning per SPEC-003-A."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.models_crud.thumbnail import generate_and_store_thumbnail
from app.search.service import index_model as _index_model
from app.search.service import remove_model_index as _remove_model_index

if TYPE_CHECKING:
    import aiosqlite


async def create_model(
    db: aiosqlite.Connection,
    *,
    model_type: str,
    name: str,
    description: str | None,
    data: dict[str, object],
    created_by: str,
) -> dict[str, object]:
    """Create a new model with initial version."""
    model_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    data_json = json.dumps(data)

    await db.execute(
        "INSERT INTO models (id, model_type, current_version, "
        "created_at, created_by, updated_at) VALUES (?, ?, 1, ?, ?, ?)",
        (model_id, model_type, now, created_by, now),
    )
    await db.execute(
        "INSERT INTO model_versions (model_id, version, name, description, "
        "data, change_type, created_at, created_by) "
        "VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
        (model_id, name, description, data_json, now, created_by),
    )
    await db.commit()
    await _index_model(
        db, model_id=model_id, name=name,
        model_type=model_type, description=description,
    )
    await db.commit()

    await generate_and_store_thumbnail(db, model_id, data, model_type)

    return {
        "id": model_id,
        "model_type": model_type,
        "current_version": 1,
        "name": name,
        "description": description,
        "data": data,
        "created_at": now,
        "created_by": created_by,
        "updated_at": now,
        "is_deleted": False,
    }


async def get_model(
    db: aiosqlite.Connection,
    model_id: str,
) -> dict[str, object] | None:
    """Get a model with its current version data."""
    cursor = await db.execute(
        "SELECT m.id, m.model_type, m.current_version, "
        "mv.name, mv.description, mv.data, "
        "m.created_at, m.created_by, m.updated_at, m.is_deleted, "
        "u.username "
        "FROM models m "
        "JOIN model_versions mv ON m.id = mv.model_id "
        "AND m.current_version = mv.version "
        "LEFT JOIN users u ON m.created_by = u.id "
        "WHERE m.id = ? AND m.is_deleted = 0",
        (model_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    return {
        "id": row[0],
        "model_type": row[1],
        "current_version": row[2],
        "name": row[3],
        "description": row[4],
        "data": json.loads(row[5]) if row[5] else {},
        "created_at": row[6],
        "created_by": row[7],
        "updated_at": row[8],
        "is_deleted": bool(row[9]),
        "created_by_username": row[10] or "Unknown",
    }


async def list_models(
    db: aiosqlite.Connection,
    *,
    model_type: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict[str, object]], int]:
    """List models with pagination."""
    where_clauses = ["m.is_deleted = 0"]
    params: list[object] = []

    if model_type:
        where_clauses.append("m.model_type = ?")
        params.append(model_type)

    where_sql = " AND ".join(where_clauses)

    cursor = await db.execute(
        f"SELECT COUNT(*) FROM models m WHERE {where_sql}",  # noqa: S608
        params,
    )
    count_row = await cursor.fetchone()
    total: int = count_row[0]  # type: ignore[index]

    offset = (page - 1) * page_size
    cursor = await db.execute(
        f"SELECT m.id, m.model_type, m.current_version, "  # noqa: S608
        "mv.name, mv.description, mv.data, "
        "m.created_at, m.created_by, m.updated_at, m.is_deleted "
        "FROM models m "
        "JOIN model_versions mv ON m.id = mv.model_id "
        "AND m.current_version = mv.version "
        f"WHERE {where_sql} "
        "ORDER BY m.updated_at DESC LIMIT ? OFFSET ?",
        [*params, page_size, offset],
    )
    rows = await cursor.fetchall()

    items = [
        {
            "id": r[0],
            "model_type": r[1],
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


async def update_model(
    db: aiosqlite.Connection,
    model_id: str,
    *,
    name: str,
    description: str | None,
    data: dict[str, object],
    change_summary: str | None,
    updated_by: str,
    expected_version: int,
) -> dict[str, object] | None:
    """Update a model with OCC."""
    cursor = await db.execute(
        "SELECT current_version FROM models WHERE id = ? AND is_deleted = 0",
        (model_id,),
    )
    row = await cursor.fetchone()
    if row is None or row[0] != expected_version:
        return None

    new_version = row[0] + 1
    now = datetime.now(tz=UTC).isoformat()
    data_json = json.dumps(data)

    await db.execute(
        "UPDATE models SET current_version = ?, updated_at = ? WHERE id = ?",
        (new_version, now, model_id),
    )
    await db.execute(
        "INSERT INTO model_versions (model_id, version, name, description, "
        "data, change_type, change_summary, created_at, created_by) "
        "VALUES (?, ?, ?, ?, ?, 'update', ?, ?, ?)",
        (model_id, new_version, name, description, data_json,
         change_summary, now, updated_by),
    )
    await db.commit()

    # Re-index for search
    type_cursor = await db.execute(
        "SELECT model_type FROM models WHERE id = ?", (model_id,),
    )
    type_row = await type_cursor.fetchone()
    if type_row:
        await _index_model(
            db, model_id=model_id, name=name,
            model_type=type_row[0], description=description,
        )
        await db.commit()

    # Generate/update thumbnail
    if type_row:
        await generate_and_store_thumbnail(db, model_id, data, type_row[0])

    return {"current_version": new_version, "updated_at": now}


async def soft_delete_model(
    db: aiosqlite.Connection,
    model_id: str,
    *,
    deleted_by: str,
    expected_version: int,
) -> bool:
    """Soft-delete a model."""
    cursor = await db.execute(
        "SELECT current_version FROM models WHERE id = ? AND is_deleted = 0",
        (model_id,),
    )
    row = await cursor.fetchone()
    if row is None or row[0] != expected_version:
        return False

    new_version = row[0] + 1
    now = datetime.now(tz=UTC).isoformat()

    cursor = await db.execute(
        "SELECT name, description, data FROM model_versions "
        "WHERE model_id = ? AND version = ?",
        (model_id, row[0]),
    )
    ver_row = await cursor.fetchone()

    await db.execute(
        "UPDATE models SET current_version = ?, updated_at = ?, "
        "is_deleted = 1 WHERE id = ?",
        (new_version, now, model_id),
    )
    await db.execute(
        "INSERT INTO model_versions (model_id, version, name, description, "
        "data, change_type, created_at, created_by) "
        "VALUES (?, ?, ?, ?, ?, 'delete', ?, ?)",
        (model_id, new_version, ver_row[0], ver_row[1],
         ver_row[2], now, deleted_by),
    )
    await db.commit()
    await _remove_model_index(db, model_id)
    await db.commit()
    return True


async def get_model_versions(
    db: aiosqlite.Connection,
    model_id: str,
) -> list[dict[str, object]]:
    """Get all versions of a model."""
    cursor = await db.execute(
        "SELECT mv.model_id, mv.version, mv.name, mv.description, mv.data, "
        "mv.change_type, mv.change_summary, mv.rollback_to, "
        "mv.created_at, mv.created_by, "
        "u.username "
        "FROM model_versions mv "
        "LEFT JOIN users u ON mv.created_by = u.id "
        "WHERE mv.model_id = ? "
        "ORDER BY mv.version DESC",
        (model_id,),
    )
    rows = await cursor.fetchall()
    return [
        {
            "model_id": r[0],
            "version": r[1],
            "name": r[2],
            "description": r[3],
            "data": json.loads(r[4]) if r[4] else {},
            "change_type": r[5],
            "change_summary": r[6],
            "rollback_to": r[7],
            "created_at": r[8],
            "created_by": r[9],
            "created_by_username": r[10] or "Unknown",
        }
        for r in rows
    ]
