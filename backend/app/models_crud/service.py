"""Model CRUD service with versioning per SPEC-003-A."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.migrations.m012_sets import DEFAULT_SET_ID
from app.models_crud.thumbnail import VALID_THEMES, generate_and_store_thumbnail
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
    parent_model_id: str | None = None,
    set_id: str | None = None,
) -> dict[str, object]:
    """Create a new model with initial version."""
    model_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    data_json = json.dumps(data)
    effective_set_id = set_id or DEFAULT_SET_ID

    await db.execute(
        "INSERT INTO models (id, model_type, current_version, "
        "created_at, created_by, updated_at, parent_model_id, set_id) "
        "VALUES (?, ?, 1, ?, ?, ?, ?, ?)",
        (model_id, model_type, now, created_by, now, parent_model_id, effective_set_id),
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

    for theme in VALID_THEMES:
        await generate_and_store_thumbnail(db, model_id, data, model_type, theme=theme)

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
        "parent_model_id": parent_model_id,
        "set_id": effective_set_id,
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
        "u.username, m.parent_model_id, m.set_id, s.name "
        "FROM models m "
        "JOIN model_versions mv ON m.id = mv.model_id "
        "AND m.current_version = mv.version "
        "LEFT JOIN users u ON m.created_by = u.id "
        "LEFT JOIN sets s ON m.set_id = s.id "
        "WHERE m.id = ? AND m.is_deleted = 0",
        (model_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    # Fetch tags for this model
    tag_cursor = await db.execute(
        "SELECT tag FROM model_tags WHERE model_id = ? ORDER BY tag",
        (model_id,),
    )
    tag_rows = await tag_cursor.fetchall()
    tags = [t[0] for t in tag_rows]

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
        "parent_model_id": row[11],
        "tags": tags,
        "set_id": row[12],
        "set_name": row[13],
    }


async def list_models(
    db: aiosqlite.Connection,
    *,
    model_type: str | None = None,
    set_id: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict[str, object]], int]:
    """List models with pagination."""
    where_clauses = ["m.is_deleted = 0"]
    params: list[object] = []

    if model_type:
        where_clauses.append("m.model_type = ?")
        params.append(model_type)

    if set_id:
        where_clauses.append("m.set_id = ?")
        params.append(set_id)

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
        "m.created_at, m.created_by, m.updated_at, m.is_deleted, "
        "m.parent_model_id, m.set_id, s.name "
        "FROM models m "
        "JOIN model_versions mv ON m.id = mv.model_id "
        "AND m.current_version = mv.version "
        "LEFT JOIN sets s ON m.set_id = s.id "
        f"WHERE {where_sql} "
        "ORDER BY m.updated_at DESC LIMIT ? OFFSET ?",
        [*params, page_size, offset],
    )
    rows = await cursor.fetchall()

    # Collect model IDs for batch tag lookup
    model_ids = [r[0] for r in rows]
    tags_by_model: dict[str, list[str]] = {mid: [] for mid in model_ids}
    if model_ids:
        placeholders = ",".join("?" for _ in model_ids)
        tag_cursor = await db.execute(
            f"SELECT model_id, tag FROM model_tags WHERE model_id IN ({placeholders}) ORDER BY tag",  # noqa: S608
            model_ids,
        )
        tag_rows = await tag_cursor.fetchall()
        for tr in tag_rows:
            tags_by_model[tr[0]].append(tr[1])

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
            "parent_model_id": r[10],
            "tags": tags_by_model.get(r[0], []),
            "set_id": r[11],
            "set_name": r[12],
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

    # Generate/update thumbnail for all themes
    if type_row:
        for theme in VALID_THEMES:
            await generate_and_store_thumbnail(db, model_id, data, type_row[0], theme=theme)

    # Auto-membership: move canvas entities to this model's set
    try:
        model_set_cursor = await db.execute(
            "SELECT set_id FROM models WHERE id = ?", (model_id,),
        )
        model_set_row = await model_set_cursor.fetchone()
        if model_set_row and model_set_row[0]:
            model_set_id = model_set_row[0]
            nodes_for_set = data.get("nodes", []) if isinstance(data, dict) else []
            for node in nodes_for_set:
                if isinstance(node, dict) and isinstance(node.get("data"), dict):
                    eid = node["data"].get("entityId")
                    if eid:
                        await db.execute(
                            "UPDATE entities SET set_id = ? WHERE id = ? AND set_id != ?",
                            (model_set_id, eid, model_set_id),
                        )
            await db.commit()
    except Exception:
        pass  # Don't fail model save if auto-membership fails

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


async def validate_no_cycle(
    db: aiosqlite.Connection,
    model_id: str,
    proposed_parent_id: str,
) -> bool:
    """Check that setting proposed_parent_id won't create a cycle.

    Walks up from proposed_parent_id to root. If we encounter model_id,
    it would create a cycle. Returns True if safe, False if cycle detected.
    """
    if model_id == proposed_parent_id:
        return False

    current = proposed_parent_id
    visited: set[str] = set()
    while current is not None:
        if current == model_id:
            return False
        if current in visited:
            return False  # existing cycle in data — shouldn't happen
        visited.add(current)
        cursor = await db.execute(
            "SELECT parent_model_id FROM models WHERE id = ? AND is_deleted = 0",
            (current,),
        )
        row = await cursor.fetchone()
        if row is None:
            break
        current = row[0]
    return True


async def set_model_parent(
    db: aiosqlite.Connection,
    model_id: str,
    parent_model_id: str | None,
    updated_by: str,
) -> dict[str, object] | None:
    """Set or unset a model's parent. Returns None on failure."""
    # Verify model exists
    cursor = await db.execute(
        "SELECT id FROM models WHERE id = ? AND is_deleted = 0",
        (model_id,),
    )
    if await cursor.fetchone() is None:
        return None

    # If setting a parent, verify parent exists and no cycle
    if parent_model_id is not None:
        cursor = await db.execute(
            "SELECT id FROM models WHERE id = ? AND is_deleted = 0",
            (parent_model_id,),
        )
        if await cursor.fetchone() is None:
            return None

        if not await validate_no_cycle(db, model_id, parent_model_id):
            return {"error": "cycle"}

    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "UPDATE models SET parent_model_id = ?, updated_at = ? WHERE id = ?",
        (parent_model_id, now, model_id),
    )
    await db.commit()
    return {"model_id": model_id, "parent_model_id": parent_model_id}


async def get_ancestors(
    db: aiosqlite.Connection,
    model_id: str,
) -> list[dict[str, object]]:
    """Get ancestor chain from model to root (breadcrumb order: root first)."""
    ancestors: list[dict[str, object]] = []
    current = model_id

    # First get the parent of the starting model
    cursor = await db.execute(
        "SELECT parent_model_id FROM models WHERE id = ? AND is_deleted = 0",
        (current,),
    )
    row = await cursor.fetchone()
    if row is None:
        return []
    current = row[0]

    visited: set[str] = set()
    while current is not None:
        if current in visited:
            break
        visited.add(current)
        cursor = await db.execute(
            "SELECT m.id, mv.name, m.model_type, m.parent_model_id "
            "FROM models m "
            "JOIN model_versions mv ON m.id = mv.model_id "
            "AND m.current_version = mv.version "
            "WHERE m.id = ? AND m.is_deleted = 0",
            (current,),
        )
        row = await cursor.fetchone()
        if row is None:
            break
        ancestors.append({
            "id": row[0],
            "name": row[1],
            "model_type": row[2],
            "parent_model_id": row[3],
        })
        current = row[3]

    ancestors.reverse()  # root first
    return ancestors


async def get_children(
    db: aiosqlite.Connection,
    model_id: str,
) -> list[dict[str, object]]:
    """Get direct children of a model."""
    cursor = await db.execute(
        "SELECT m.id, mv.name, m.model_type, m.parent_model_id "
        "FROM models m "
        "JOIN model_versions mv ON m.id = mv.model_id "
        "AND m.current_version = mv.version "
        "WHERE m.parent_model_id = ? AND m.is_deleted = 0 "
        "ORDER BY mv.name",
        (model_id,),
    )
    rows = await cursor.fetchall()
    return [
        {
            "id": r[0],
            "name": r[1],
            "model_type": r[2],
            "parent_model_id": r[3],
        }
        for r in rows
    ]


async def get_model_hierarchy(
    db: aiosqlite.Connection,
    root_id: str | None = None,
    set_id: str | None = None,
) -> list[dict[str, object]]:
    """Get the model hierarchy as a tree.

    If root_id is given, returns subtree rooted at that model.
    If set_id is given, only includes models from that set.
    Otherwise returns all root models with their children.
    """
    # Fetch all non-deleted models (optionally filtered by set)
    query = (
        "SELECT m.id, mv.name, m.model_type, m.parent_model_id "
        "FROM models m "
        "JOIN model_versions mv ON m.id = mv.model_id "
        "AND m.current_version = mv.version "
        "WHERE m.is_deleted = 0 "
    )
    params: list[str] = []
    if set_id is not None:
        query += "AND m.set_id = ? "
        params.append(set_id)
    query += "ORDER BY mv.name"
    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()

    # Build lookup structures
    nodes: dict[str, dict[str, object]] = {}
    for r in rows:
        nodes[r[0]] = {
            "id": r[0],
            "name": r[1],
            "model_type": r[2],
            "parent_model_id": r[3],
            "children": [],
        }

    # Build tree
    roots: list[dict[str, object]] = []
    for node in nodes.values():
        parent_id = node["parent_model_id"]
        if parent_id is not None and parent_id in nodes:
            parent_children: list[dict[str, object]] = nodes[parent_id]["children"]  # type: ignore[assignment]
            parent_children.append(node)
        elif parent_id is None or parent_id not in nodes:
            roots.append(node)

    if root_id is not None:
        # Return subtree rooted at root_id
        if root_id in nodes:
            return [nodes[root_id]]
        return []

    return roots


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
