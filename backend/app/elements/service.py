"""Element CRUD service with versioning per SPEC-006-A."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.migrations.m012_sets import DEFAULT_SET_ID
from app.search.service import index_element as _index_element
from app.search.service import remove_element_index as _remove_element_index

if TYPE_CHECKING:
    import aiosqlite


async def create_element(
    db: aiosqlite.Connection,
    *,
    element_type: str,
    name: str,
    description: str | None,
    data: dict[str, object],
    created_by: str,
    set_id: str | None = None,
    metadata: dict[str, object] | None = None,
    change_summary: str | None = None,
) -> dict[str, object]:
    """Create a new element with initial version."""
    element_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    data_json = json.dumps(data)
    metadata_json = json.dumps(metadata) if metadata else None
    effective_set_id = set_id or DEFAULT_SET_ID

    await db.execute(
        "INSERT INTO elements (id, element_type, current_version, "
        "created_at, created_by, updated_at, set_id) VALUES (?, ?, 1, ?, ?, ?, ?)",
        (element_id, element_type, now, created_by, now, effective_set_id),
    )
    await db.execute(
        "INSERT INTO element_versions (element_id, version, name, description, "
        "data, change_type, change_summary, created_at, created_by, metadata) "
        "VALUES (?, 1, ?, ?, ?, 'create', ?, ?, ?, ?)",
        (element_id, name, description, data_json, change_summary, now, created_by, metadata_json),
    )
    await db.commit()
    await _index_element(
        db, element_id=element_id, name=name,
        element_type=element_type, description=description,
    )
    await db.commit()

    return {
        "id": element_id,
        "element_type": element_type,
        "current_version": 1,
        "name": name,
        "description": description,
        "data": data,
        "created_at": now,
        "created_by": created_by,
        "updated_at": now,
        "is_deleted": False,
        "set_id": effective_set_id,
        "metadata": metadata,
    }


async def get_element(
    db: aiosqlite.Connection,
    element_id: str,
) -> dict[str, object] | None:
    """Get an element with its current version data."""
    cursor = await db.execute(
        "SELECT e.id, e.element_type, e.current_version, "
        "ev.name, ev.description, ev.data, "
        "e.created_at, e.created_by, e.updated_at, e.is_deleted, "
        "u.username, e.set_id, s.name, ev.metadata "
        "FROM elements e "
        "JOIN element_versions ev ON e.id = ev.element_id "
        "AND e.current_version = ev.version "
        "LEFT JOIN users u ON e.created_by = u.id "
        "LEFT JOIN sets s ON e.set_id = s.id "
        "WHERE e.id = ? AND e.is_deleted = 0",
        (element_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    element = {
        "id": row[0],
        "element_type": row[1],
        "current_version": row[2],
        "name": row[3],
        "description": row[4],
        "data": json.loads(row[5]) if row[5] else {},
        "created_at": row[6],
        "created_by": row[7],
        "updated_at": row[8],
        "is_deleted": bool(row[9]),
        "created_by_username": row[10] or "Unknown",
        "set_id": row[11],
        "set_name": row[12],
        "metadata": json.loads(row[13]) if row[13] else None,
    }

    # Enrich with tags
    tag_cursor = await db.execute(
        "SELECT tag FROM element_tags WHERE element_id = ? ORDER BY tag",
        (element_id,),
    )
    tag_rows = await tag_cursor.fetchall()
    element["tags"] = [r[0] for r in tag_rows]

    return element


async def list_elements(
    db: aiosqlite.Connection,
    *,
    element_type: str | None = None,
    set_id: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict[str, object]], int]:
    """List elements with pagination. Returns (items, total_count)."""
    where_clauses = ["e.is_deleted = 0"]
    params: list[object] = []

    if element_type:
        where_clauses.append("e.element_type = ?")
        params.append(element_type)

    if set_id:
        where_clauses.append("e.set_id = ?")
        params.append(set_id)

    where_sql = " AND ".join(where_clauses)

    # Count
    cursor = await db.execute(
        f"SELECT COUNT(*) FROM elements e WHERE {where_sql}",  # noqa: S608
        params,
    )
    count_row = await cursor.fetchone()
    total: int = count_row[0]  # type: ignore[index]

    # Fetch page
    offset = (page - 1) * page_size
    cursor = await db.execute(
        f"SELECT e.id, e.element_type, e.current_version, "  # noqa: S608
        "ev.name, ev.description, ev.data, "
        "e.created_at, e.created_by, e.updated_at, e.is_deleted, "
        "e.set_id, s.name, ev.metadata "
        "FROM elements e "
        "JOIN element_versions ev ON e.id = ev.element_id "
        "AND e.current_version = ev.version "
        "LEFT JOIN sets s ON e.set_id = s.id "
        f"WHERE {where_sql} "
        "ORDER BY e.updated_at DESC LIMIT ? OFFSET ?",
        [*params, page_size, offset],
    )
    rows = await cursor.fetchall()

    items = [
        {
            "id": r[0],
            "element_type": r[1],
            "current_version": r[2],
            "name": r[3],
            "description": r[4],
            "data": json.loads(r[5]) if r[5] else {},
            "created_at": r[6],
            "created_by": r[7],
            "updated_at": r[8],
            "is_deleted": bool(r[9]),
            "set_id": r[10],
            "set_name": r[11],
            "metadata": json.loads(r[12]) if r[12] else None,
        }
        for r in rows
    ]

    # Enrich with tags and stats
    for item in items:
        element_id = item["id"]

        # Tags
        tag_cursor = await db.execute(
            "SELECT tag FROM element_tags WHERE element_id = ? ORDER BY tag",
            (element_id,),
        )
        tag_rows = await tag_cursor.fetchall()
        item["tags"] = [r[0] for r in tag_rows]

        # Relationship count
        rel_cursor = await db.execute(
            "SELECT COUNT(*) FROM relationships "
            "WHERE (source_element_id = ? OR target_element_id = ?) AND is_deleted = 0",
            (element_id, element_id),
        )
        rel_row = await rel_cursor.fetchone()
        item["relationship_count"] = rel_row[0] if rel_row else 0

        # Diagram usage count
        diagram_cursor = await db.execute(
            "SELECT COUNT(DISTINCT d.id) FROM diagrams d "
            "JOIN diagram_versions dv ON d.id = dv.diagram_id AND d.current_version = dv.version "
            "WHERE d.is_deleted = 0 AND dv.data LIKE ?",
            (f'%{element_id}%',),
        )
        diagram_row = await diagram_cursor.fetchone()
        item["diagram_usage_count"] = diagram_row[0] if diagram_row else 0

    return items, total


async def update_element(
    db: aiosqlite.Connection,
    element_id: str,
    *,
    name: str,
    description: str | None,
    data: dict[str, object],
    change_summary: str | None,
    updated_by: str,
    expected_version: int,
    metadata: dict[str, object] | None = None,
) -> dict[str, object] | None:
    """Update an element with optimistic concurrency. Returns None on conflict."""
    # Check current version (OCC)
    cursor = await db.execute(
        "SELECT current_version FROM elements WHERE id = ? AND is_deleted = 0",
        (element_id,),
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
    metadata_json = json.dumps(metadata) if metadata else None

    await db.execute(
        "UPDATE elements SET current_version = ?, updated_at = ? WHERE id = ?",
        (new_version, now, element_id),
    )
    await db.execute(
        "INSERT INTO element_versions (element_id, version, name, description, "
        "data, change_type, change_summary, created_at, created_by, metadata) "
        "VALUES (?, ?, ?, ?, ?, 'update', ?, ?, ?, ?)",
        (element_id, new_version, name, description, data_json,
         change_summary, now, updated_by, metadata_json),
    )
    await db.commit()

    # Re-index for search — need element_type from the element row
    type_cursor = await db.execute(
        "SELECT element_type FROM elements WHERE id = ?", (element_id,),
    )
    type_row = await type_cursor.fetchone()
    if type_row:
        await _index_element(
            db, element_id=element_id, name=name,
            element_type=type_row[0], description=description,
        )
        await db.commit()

    return {
        "id": element_id,
        "current_version": new_version,
        "name": name,
        "description": description,
        "data": data,
        "updated_at": now,
    }


async def rollback_element(
    db: aiosqlite.Connection,
    element_id: str,
    *,
    target_version: int,
    rolled_back_by: str,
    expected_version: int,
) -> dict[str, object] | None:
    """Rollback element to a previous version (creates new version). Returns None on conflict."""
    # Check current version (OCC)
    cursor = await db.execute(
        "SELECT current_version FROM elements WHERE id = ? AND is_deleted = 0",
        (element_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    current_version: int = row[0]
    if current_version != expected_version:
        return None

    # Get target version data
    cursor = await db.execute(
        "SELECT name, description, data FROM element_versions "
        "WHERE element_id = ? AND version = ?",
        (element_id, target_version),
    )
    target_row = await cursor.fetchone()
    if target_row is None:
        return None

    new_version = current_version + 1
    now = datetime.now(tz=UTC).isoformat()

    await db.execute(
        "UPDATE elements SET current_version = ?, updated_at = ? WHERE id = ?",
        (new_version, now, element_id),
    )
    await db.execute(
        "INSERT INTO element_versions (element_id, version, name, description, "
        "data, change_type, rollback_to, created_at, created_by) "
        "VALUES (?, ?, ?, ?, ?, 'rollback', ?, ?, ?)",
        (element_id, new_version, target_row[0], target_row[1],
         target_row[2], target_version, now, rolled_back_by),
    )
    await db.commit()

    # Re-index for search after rollback
    type_cursor = await db.execute(
        "SELECT element_type FROM elements WHERE id = ?", (element_id,),
    )
    type_row = await type_cursor.fetchone()
    if type_row:
        await _index_element(
            db, element_id=element_id, name=target_row[0],
            element_type=type_row[0], description=target_row[1],
        )
        await db.commit()

    return {
        "id": element_id,
        "current_version": new_version,
        "name": target_row[0],
        "description": target_row[1],
        "data": json.loads(target_row[2]) if target_row[2] else {},
        "updated_at": now,
    }


async def soft_delete_element(
    db: aiosqlite.Connection,
    element_id: str,
    *,
    deleted_by: str,
    expected_version: int,
) -> bool:
    """Soft-delete an element. Returns False on conflict or not found."""
    cursor = await db.execute(
        "SELECT current_version FROM elements WHERE id = ? AND is_deleted = 0",
        (element_id,),
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
        "SELECT name, description, data FROM element_versions "
        "WHERE element_id = ? AND version = ?",
        (element_id, current_version),
    )
    ver_row = await cursor.fetchone()

    await db.execute(
        "UPDATE elements SET current_version = ?, updated_at = ?, "
        "is_deleted = 1 WHERE id = ?",
        (new_version, now, element_id),
    )
    await db.execute(
        "INSERT INTO element_versions (element_id, version, name, description, "
        "data, change_type, created_at, created_by) "
        "VALUES (?, ?, ?, ?, ?, 'delete', ?, ?)",
        (element_id, new_version, ver_row[0], ver_row[1],
         ver_row[2], now, deleted_by),
    )
    await db.commit()
    await _remove_element_index(db, element_id)
    await db.commit()
    return True


async def cascade_delete_element(
    db: aiosqlite.Connection,
    element_id: str,
    *,
    deleted_by: str,
    expected_version: int,
) -> bool:
    """Cascade-delete an element: soft-delete element, relationships, and remove from all diagram canvases."""
    # 1. Soft-delete the element itself
    deleted = await soft_delete_element(
        db, element_id, deleted_by=deleted_by, expected_version=expected_version,
    )
    if not deleted:
        return False

    # 2. Soft-delete all relationships where element is source or target
    rel_cursor = await db.execute(
        "SELECT id, current_version FROM relationships "
        "WHERE (source_element_id = ? OR target_element_id = ?) AND is_deleted = 0",
        (element_id, element_id),
    )
    rel_rows = await rel_cursor.fetchall()
    for rel_row in rel_rows:
        rel_id, rel_version = rel_row[0], rel_row[1]
        now = datetime.now(tz=UTC).isoformat()
        new_version = rel_version + 1
        # Get current version data for the delete record
        ver_cursor = await db.execute(
            "SELECT label, description, data FROM relationship_versions "
            "WHERE relationship_id = ? AND version = ?",
            (rel_id, rel_version),
        )
        ver_row = await ver_cursor.fetchone()
        await db.execute(
            "UPDATE relationships SET current_version = ?, updated_at = ?, "
            "is_deleted = 1 WHERE id = ?",
            (new_version, now, rel_id),
        )
        if ver_row:
            await db.execute(
                "INSERT INTO relationship_versions "
                "(relationship_id, version, label, description, data, "
                "change_type, created_at, created_by) "
                "VALUES (?, ?, ?, ?, ?, 'delete', ?, ?)",
                (rel_id, new_version, ver_row[0], ver_row[1], ver_row[2], now, deleted_by),
            )
    await db.commit()

    # 3. Remove element from all diagram canvases
    diagram_cursor = await db.execute(
        "SELECT d.id, d.current_version, dv.name, dv.description, dv.data, dv.metadata "
        "FROM diagrams d "
        "JOIN diagram_versions dv ON d.id = dv.diagram_id AND d.current_version = dv.version "
        "WHERE d.is_deleted = 0 AND dv.data LIKE ?",
        (f"%{element_id}%",),
    )
    diagram_rows = await diagram_cursor.fetchall()
    for drow in diagram_rows:
        diagram_id, diagram_version, d_name, d_desc, d_data_str, d_meta = drow
        try:
            canvas = json.loads(d_data_str) if isinstance(d_data_str, str) else d_data_str
            if not isinstance(canvas, dict):
                continue
            nodes = canvas.get("nodes", [])
            edges = canvas.get("edges", [])
            # Find node IDs that reference this element
            removed_node_ids = {
                n["id"] for n in nodes
                if isinstance(n, dict) and isinstance(n.get("data"), dict)
                and n["data"].get("entityId") == element_id
            }
            if not removed_node_ids:
                continue
            # Remove matching nodes and connected edges
            new_nodes = [n for n in nodes if n.get("id") not in removed_node_ids]
            new_edges = [
                e for e in edges
                if e.get("source") not in removed_node_ids
                and e.get("target") not in removed_node_ids
            ]
            canvas["nodes"] = new_nodes
            canvas["edges"] = new_edges

            # Save updated canvas as new diagram version
            new_diagram_version = diagram_version + 1
            now = datetime.now(tz=UTC).isoformat()
            data_json = json.dumps(canvas)
            await db.execute(
                "UPDATE diagrams SET current_version = ?, updated_at = ? WHERE id = ?",
                (new_diagram_version, now, diagram_id),
            )
            await db.execute(
                "INSERT INTO diagram_versions (diagram_id, version, name, description, "
                "data, change_type, change_summary, created_at, created_by, metadata) "
                "VALUES (?, ?, ?, ?, ?, 'update', ?, ?, ?, ?)",
                (diagram_id, new_diagram_version, d_name, d_desc, data_json,
                 f"Removed deleted element {element_id}", now, deleted_by, d_meta),
            )
        except (json.JSONDecodeError, TypeError):
            continue
    await db.commit()
    return True


async def get_element_versions(
    db: aiosqlite.Connection,
    element_id: str,
) -> list[dict[str, object]]:
    """Get all versions of an element."""
    cursor = await db.execute(
        "SELECT ev.element_id, ev.version, ev.name, ev.description, ev.data, "
        "ev.change_type, ev.change_summary, ev.rollback_to, "
        "ev.created_at, ev.created_by, "
        "u.username, ev.metadata "
        "FROM element_versions ev "
        "LEFT JOIN users u ON ev.created_by = u.id "
        "WHERE ev.element_id = ? "
        "ORDER BY ev.version DESC",
        (element_id,),
    )
    rows = await cursor.fetchall()
    return [
        {
            "element_id": r[0],
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
            "metadata": json.loads(r[11]) if r[11] else None,
        }
        for r in rows
    ]


async def get_element_version(
    db: aiosqlite.Connection,
    element_id: str,
    version: int,
) -> dict[str, object] | None:
    """Get a specific version of an element."""
    cursor = await db.execute(
        "SELECT element_id, version, name, description, data, "
        "change_type, change_summary, rollback_to, "
        "created_at, created_by "
        "FROM element_versions WHERE element_id = ? AND version = ?",
        (element_id, version),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    return {
        "element_id": row[0],
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
