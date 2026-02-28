"""Model CRUD service with versioning per SPEC-003-A."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.relationships.service import create_relationship
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
        "m.created_at, m.created_by, m.updated_at, m.is_deleted "
        "FROM models m "
        "JOIN model_versions mv ON m.id = mv.model_id "
        "AND m.current_version = mv.version "
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

    # Auto-create entity relationships from canvas edges
    try:
        nodes_list = data.get("nodes", []) if isinstance(data, dict) else []
        edges_list = data.get("edges", []) if isinstance(data, dict) else []

        # Build node_id -> entityId mapping
        node_entity_map: dict[str, str] = {}
        for node in nodes_list:
            if isinstance(node, dict) and isinstance(node.get("data"), dict):
                entity_id = node["data"].get("entityId")
                if entity_id:
                    node_entity_map[node["id"]] = entity_id

        # For each edge where both source and target have entityIds, create relationship
        for edge in edges_list:
            if not isinstance(edge, dict):
                continue
            source_entity = node_entity_map.get(edge.get("source", ""))
            target_entity = node_entity_map.get(edge.get("target", ""))
            if source_entity and target_entity and source_entity != target_entity:
                # Check if relationship already exists
                cursor = await db.execute(
                    "SELECT id FROM relationships "
                    "WHERE source_entity_id = ? AND target_entity_id = ? AND is_deleted = 0",
                    (source_entity, target_entity),
                )
                existing = await cursor.fetchone()
                if not existing:
                    rel_type = "uses"
                    if isinstance(edge.get("data"), dict):
                        rel_type = edge["data"].get("relationshipType", "uses")
                    await create_relationship(
                        db,
                        source_entity_id=source_entity,
                        target_entity_id=target_entity,
                        relationship_type=rel_type,
                        label=None,
                        description=None,
                        data={},
                        created_by=updated_by,
                    )
    except Exception:
        pass  # Don't fail model save if relationship auto-creation fails

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
        "SELECT model_id, version, name, description, data, "
        "change_type, change_summary, rollback_to, "
        "created_at, created_by "
        "FROM model_versions WHERE model_id = ? "
        "ORDER BY version DESC",
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
        }
        for r in rows
    ]
