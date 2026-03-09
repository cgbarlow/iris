"""Diagram CRUD service with versioning per SPEC-003-A."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.migrations.m012_sets import DEFAULT_SET_ID
from app.diagrams.thumbnail import VALID_THEMES, generate_and_store_thumbnail
from app.package_relationships.service import create_package_relationship
from app.relationships.service import create_relationship
from app.diagrams.notation_detection import detect_notations as _detect_notations
from app.diagrams.registry_service import get_default_notation, validate_type_notation
from app.search.service import index_diagram as _index_diagram
from app.search.service import remove_diagram_index as _remove_diagram_index

if TYPE_CHECKING:
    import aiosqlite


async def create_diagram(
    db: aiosqlite.Connection,
    *,
    diagram_type: str,
    name: str,
    description: str | None,
    data: dict[str, object],
    created_by: str,
    parent_package_id: str | None = None,
    set_id: str | None = None,
    notation: str | None = None,
    metadata: dict[str, object] | None = None,
    change_summary: str | None = None,
) -> dict[str, object]:
    """Create a new diagram with initial version."""
    diagram_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    data_json = json.dumps(data)
    metadata_json = json.dumps(metadata) if metadata else None
    effective_set_id = set_id or DEFAULT_SET_ID

    # Validate set_id exists — fall back to default if not
    cursor = await db.execute(
        "SELECT 1 FROM sets WHERE id = ?", (effective_set_id,)
    )
    if await cursor.fetchone() is None:
        effective_set_id = DEFAULT_SET_ID

    # Resolve notation: use provided, else default from registry, else 'simple'
    effective_notation = notation
    if not effective_notation:
        default = await get_default_notation(db, diagram_type)
        effective_notation = default or "simple"

    # Validate (type, notation) pair if both are known
    if effective_notation:
        is_valid = await validate_type_notation(db, diagram_type, effective_notation)
        if not is_valid:
            # Fallback to default rather than rejecting
            default = await get_default_notation(db, diagram_type)
            effective_notation = default or "simple"

    # Auto-detect notations from canvas data
    detected = _detect_notations(data) if isinstance(data, dict) else []
    detected_json = json.dumps(detected)

    await db.execute(
        "INSERT INTO diagrams (id, diagram_type, current_version, "
        "created_at, created_by, updated_at, parent_package_id, set_id, "
        "notation, detected_notations) "
        "VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?)",
        (diagram_id, diagram_type, now, created_by, now,
         parent_package_id, effective_set_id, effective_notation, detected_json),
    )
    await db.execute(
        "INSERT INTO diagram_versions (diagram_id, version, name, description, "
        "data, change_type, change_summary, created_at, created_by, metadata) "
        "VALUES (?, 1, ?, ?, ?, 'create', ?, ?, ?, ?)",
        (diagram_id, name, description, data_json, change_summary, now, created_by, metadata_json),
    )
    await db.commit()
    await _index_diagram(
        db, diagram_id=diagram_id, name=name,
        diagram_type=diagram_type, description=description,
    )
    await db.commit()

    for theme in VALID_THEMES:
        await generate_and_store_thumbnail(db, diagram_id, data, diagram_type, theme=theme)

    return {
        "id": diagram_id,
        "diagram_type": diagram_type,
        "current_version": 1,
        "name": name,
        "description": description,
        "data": data,
        "created_at": now,
        "created_by": created_by,
        "updated_at": now,
        "is_deleted": False,
        "parent_package_id": parent_package_id,
        "set_id": effective_set_id,
        "notation": effective_notation,
        "detected_notations": detected,
        "metadata": metadata,
    }


async def get_diagram(
    db: aiosqlite.Connection,
    diagram_id: str,
) -> dict[str, object] | None:
    """Get a diagram with its current version data."""
    cursor = await db.execute(
        "SELECT d.id, d.diagram_type, d.current_version, "
        "dv.name, dv.description, dv.data, "
        "d.created_at, d.created_by, d.updated_at, d.is_deleted, "
        "u.username, d.parent_package_id, d.set_id, s.name, dv.metadata, "
        "d.notation, d.detected_notations "
        "FROM diagrams d "
        "JOIN diagram_versions dv ON d.id = dv.diagram_id "
        "AND d.current_version = dv.version "
        "LEFT JOIN users u ON d.created_by = u.id "
        "LEFT JOIN sets s ON d.set_id = s.id "
        "WHERE d.id = ? AND d.is_deleted = 0",
        (diagram_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    # Fetch tags for this diagram
    tag_cursor = await db.execute(
        "SELECT tag FROM diagram_tags WHERE diagram_id = ? ORDER BY tag",
        (diagram_id,),
    )
    tag_rows = await tag_cursor.fetchall()
    tags = [t[0] for t in tag_rows]

    # Parse detected_notations JSON
    detected_raw = row[16]
    try:
        detected = json.loads(detected_raw) if detected_raw else []
    except (json.JSONDecodeError, TypeError):
        detected = []

    return {
        "id": row[0],
        "diagram_type": row[1],
        "current_version": row[2],
        "name": row[3],
        "description": row[4],
        "data": json.loads(row[5]) if row[5] else {},
        "created_at": row[6],
        "created_by": row[7],
        "updated_at": row[8],
        "is_deleted": bool(row[9]),
        "created_by_username": row[10] or "Unknown",
        "parent_package_id": row[11],
        "tags": tags,
        "set_id": row[12],
        "set_name": row[13],
        "notation": row[15] or "simple",
        "detected_notations": detected,
        "metadata": json.loads(row[14]) if row[14] else None,
    }


async def list_diagrams(
    db: aiosqlite.Connection,
    *,
    diagram_type: str | None = None,
    notation: str | None = None,
    set_id: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict[str, object]], int]:
    """List diagrams with pagination."""
    where_clauses = ["d.is_deleted = 0"]
    params: list[object] = []

    if diagram_type:
        where_clauses.append("d.diagram_type = ?")
        params.append(diagram_type)

    if notation:
        where_clauses.append("d.notation = ?")
        params.append(notation)

    if set_id:
        where_clauses.append("d.set_id = ?")
        params.append(set_id)

    where_sql = " AND ".join(where_clauses)

    cursor = await db.execute(
        f"SELECT COUNT(*) FROM diagrams d WHERE {where_sql}",  # noqa: S608
        params,
    )
    count_row = await cursor.fetchone()
    total: int = count_row[0]  # type: ignore[index]

    offset = (page - 1) * page_size
    cursor = await db.execute(
        f"SELECT d.id, d.diagram_type, d.current_version, "  # noqa: S608
        "dv.name, dv.description, dv.data, "
        "d.created_at, d.created_by, d.updated_at, d.is_deleted, "
        "d.parent_package_id, d.set_id, s.name, dv.metadata, "
        "d.notation, d.detected_notations "
        "FROM diagrams d "
        "JOIN diagram_versions dv ON d.id = dv.diagram_id "
        "AND d.current_version = dv.version "
        "LEFT JOIN sets s ON d.set_id = s.id "
        f"WHERE {where_sql} "
        "ORDER BY d.updated_at DESC LIMIT ? OFFSET ?",
        [*params, page_size, offset],
    )
    rows = await cursor.fetchall()

    # Collect diagram IDs for batch tag lookup
    diagram_ids = [r[0] for r in rows]
    tags_by_diagram: dict[str, list[str]] = {did: [] for did in diagram_ids}
    if diagram_ids:
        placeholders = ",".join("?" for _ in diagram_ids)
        tag_cursor = await db.execute(
            f"SELECT diagram_id, tag FROM diagram_tags WHERE diagram_id IN ({placeholders}) ORDER BY tag",  # noqa: S608
            diagram_ids,
        )
        tag_rows = await tag_cursor.fetchall()
        for tr in tag_rows:
            tags_by_diagram[tr[0]].append(tr[1])

    items = []
    for r in rows:
        detected_raw = r[15 + 0]  # notation is index 14, detected_notations is 15
        # Actually: indices are 0-15. notation=14, detected_notations=15
        try:
            detected = json.loads(r[15]) if r[15] else []
        except (json.JSONDecodeError, TypeError):
            detected = []
        items.append({
            "id": r[0],
            "diagram_type": r[1],
            "current_version": r[2],
            "name": r[3],
            "description": r[4],
            "data": json.loads(r[5]) if r[5] else {},
            "created_at": r[6],
            "created_by": r[7],
            "updated_at": r[8],
            "is_deleted": bool(r[9]),
            "parent_package_id": r[10],
            "tags": tags_by_diagram.get(r[0], []),
            "set_id": r[11],
            "set_name": r[12],
            "notation": r[14] or "simple",
            "detected_notations": detected,
            "metadata": json.loads(r[13]) if r[13] else None,
        })
    return items, total


async def update_diagram(
    db: aiosqlite.Connection,
    diagram_id: str,
    *,
    name: str,
    description: str | None,
    data: dict[str, object],
    change_summary: str | None,
    updated_by: str,
    expected_version: int,
    metadata: dict[str, object] | None = None,
) -> dict[str, object] | None:
    """Update a diagram with OCC."""
    cursor = await db.execute(
        "SELECT current_version FROM diagrams WHERE id = ? AND is_deleted = 0",
        (diagram_id,),
    )
    row = await cursor.fetchone()
    if row is None or row[0] != expected_version:
        return None

    new_version = row[0] + 1
    now = datetime.now(tz=UTC).isoformat()
    data_json = json.dumps(data)
    metadata_json = json.dumps(metadata) if metadata else None

    # Auto-detect notations from canvas data
    detected = _detect_notations(data) if isinstance(data, dict) else []
    detected_json = json.dumps(detected)

    await db.execute(
        "UPDATE diagrams SET current_version = ?, updated_at = ?, "
        "detected_notations = ? WHERE id = ?",
        (new_version, now, detected_json, diagram_id),
    )
    await db.execute(
        "INSERT INTO diagram_versions (diagram_id, version, name, description, "
        "data, change_type, change_summary, created_at, created_by, metadata) "
        "VALUES (?, ?, ?, ?, ?, 'update', ?, ?, ?, ?)",
        (diagram_id, new_version, name, description, data_json,
         change_summary, now, updated_by, metadata_json),
    )
    await db.commit()

    # Re-index for search
    type_cursor = await db.execute(
        "SELECT diagram_type FROM diagrams WHERE id = ?", (diagram_id,),
    )
    type_row = await type_cursor.fetchone()
    if type_row:
        await _index_diagram(
            db, diagram_id=diagram_id, name=name,
            diagram_type=type_row[0], description=description,
        )
        await db.commit()

    # Generate/update thumbnail for all themes
    if type_row:
        for theme in VALID_THEMES:
            await generate_and_store_thumbnail(db, diagram_id, data, type_row[0], theme=theme)

    # Auto-membership: move canvas elements to this diagram's set
    try:
        diagram_set_cursor = await db.execute(
            "SELECT set_id FROM diagrams WHERE id = ?", (diagram_id,),
        )
        diagram_set_row = await diagram_set_cursor.fetchone()
        if diagram_set_row and diagram_set_row[0]:
            diagram_set_id = diagram_set_row[0]
            nodes_for_set = data.get("nodes", []) if isinstance(data, dict) else []
            for node in nodes_for_set:
                if isinstance(node, dict) and isinstance(node.get("data"), dict):
                    eid = node["data"].get("entityId")
                    if eid:
                        await db.execute(
                            "UPDATE elements SET set_id = ? WHERE id = ? AND set_id != ?",
                            (diagram_set_id, eid, diagram_set_id),
                        )
            await db.commit()
    except Exception:
        pass  # Don't fail diagram save if auto-membership fails

    # Auto-create element relationships from canvas edges
    try:
        nodes_list = data.get("nodes", []) if isinstance(data, dict) else []
        edges_list = data.get("edges", []) if isinstance(data, dict) else []

        # Build node_id -> entityId mapping
        node_entity_map: dict[str, str] = {}
        for node in nodes_list:
            if isinstance(node, dict) and isinstance(node.get("data"), dict):
                element_id = node["data"].get("entityId")
                if element_id:
                    node_entity_map[node["id"]] = element_id

        # For each edge where both source and target have element IDs, create relationship
        for edge in edges_list:
            if not isinstance(edge, dict):
                continue
            source_element = node_entity_map.get(edge.get("source", ""))
            target_element = node_entity_map.get(edge.get("target", ""))
            if source_element and target_element:
                # Check if relationship already exists
                cursor = await db.execute(
                    "SELECT id FROM relationships "
                    "WHERE source_element_id = ? AND target_element_id = ? AND is_deleted = 0",
                    (source_element, target_element),
                )
                existing = await cursor.fetchone()
                if not existing:
                    rel_type = "uses"
                    if isinstance(edge.get("data"), dict):
                        rel_type = edge["data"].get("relationshipType", "uses")
                    await create_relationship(
                        db,
                        source_element_id=source_element,
                        target_element_id=target_element,
                        relationship_type=rel_type,
                        label=None,
                        description=None,
                        data={},
                        created_by=updated_by,
                    )
    except Exception:
        pass  # Don't fail diagram save if relationship auto-creation fails

    # Auto-create package relationships from canvas modelref-to-modelref edges
    try:
        nodes_list_mr = data.get("nodes", []) if isinstance(data, dict) else []
        edges_list_mr = data.get("edges", []) if isinstance(data, dict) else []

        # Build node_id -> linkedPackageId mapping
        node_package_map: dict[str, str] = {}
        for node in nodes_list_mr:
            if isinstance(node, dict) and isinstance(node.get("data"), dict):
                linked_package_id = node["data"].get("linkedPackageId")
                if linked_package_id:
                    node_package_map[node["id"]] = linked_package_id

        # For each edge where both source and target are package refs, create package relationship
        for edge in edges_list_mr:
            if not isinstance(edge, dict):
                continue
            source_package = node_package_map.get(edge.get("source", ""))
            target_package = node_package_map.get(edge.get("target", ""))
            if source_package and target_package:
                rel_type = "uses"
                if isinstance(edge.get("data"), dict):
                    rel_type = edge["data"].get("relationshipType", "uses")
                # Check if relationship already exists
                cursor = await db.execute(
                    "SELECT id FROM package_relationships "
                    "WHERE source_package_id = ? AND target_package_id = ? "
                    "AND relationship_type = ?",
                    (source_package, target_package, rel_type),
                )
                existing = await cursor.fetchone()
                if not existing:
                    await create_package_relationship(
                        db,
                        source_package_id=source_package,
                        target_package_id=target_package,
                        relationship_type=rel_type,
                        created_by=updated_by,
                    )
    except Exception:
        pass  # Don't fail diagram save if package relationship auto-creation fails

    return {"current_version": new_version, "updated_at": now}


async def soft_delete_diagram(
    db: aiosqlite.Connection,
    diagram_id: str,
    *,
    deleted_by: str,
    expected_version: int,
) -> bool:
    """Soft-delete a diagram."""
    cursor = await db.execute(
        "SELECT current_version FROM diagrams WHERE id = ? AND is_deleted = 0",
        (diagram_id,),
    )
    row = await cursor.fetchone()
    if row is None or row[0] != expected_version:
        return False

    new_version = row[0] + 1
    now = datetime.now(tz=UTC).isoformat()

    cursor = await db.execute(
        "SELECT name, description, data FROM diagram_versions "
        "WHERE diagram_id = ? AND version = ?",
        (diagram_id, row[0]),
    )
    ver_row = await cursor.fetchone()

    await db.execute(
        "UPDATE diagrams SET current_version = ?, updated_at = ?, "
        "is_deleted = 1 WHERE id = ?",
        (new_version, now, diagram_id),
    )
    await db.execute(
        "INSERT INTO diagram_versions (diagram_id, version, name, description, "
        "data, change_type, created_at, created_by) "
        "VALUES (?, ?, ?, ?, ?, 'delete', ?, ?)",
        (diagram_id, new_version, ver_row[0], ver_row[1],
         ver_row[2], now, deleted_by),
    )
    await db.commit()
    await _remove_diagram_index(db, diagram_id)
    await db.commit()
    return True


async def restore_diagram(
    db: aiosqlite.Connection,
    diagram_id: str,
    *,
    restored_by: str,
) -> bool:
    """Restore a soft-deleted diagram."""
    cursor = await db.execute(
        "SELECT current_version, diagram_type FROM diagrams "
        "WHERE id = ? AND is_deleted = 1",
        (diagram_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return False

    new_version = row[0] + 1
    diagram_type = row[1]
    now = datetime.now(tz=UTC).isoformat()

    cursor = await db.execute(
        "SELECT name, description, data FROM diagram_versions "
        "WHERE diagram_id = ? AND version = ?",
        (diagram_id, row[0]),
    )
    ver_row = await cursor.fetchone()

    await db.execute(
        "UPDATE diagrams SET current_version = ?, updated_at = ?, "
        "is_deleted = 0, deleted_group_id = NULL WHERE id = ?",
        (new_version, now, diagram_id),
    )
    await db.execute(
        "INSERT INTO diagram_versions (diagram_id, version, name, description, "
        "data, change_type, created_at, created_by) "
        "VALUES (?, ?, ?, ?, ?, 'restore', ?, ?)",
        (diagram_id, new_version, ver_row[0], ver_row[1],
         ver_row[2], now, restored_by),
    )
    await db.commit()

    # Re-index for search
    await _index_diagram(
        db, diagram_id=diagram_id, name=ver_row[0],
        diagram_type=diagram_type, description=ver_row[1],
    )
    await db.commit()

    return True


async def validate_no_cycle(
    db: aiosqlite.Connection,
    diagram_id: str,
    proposed_parent_id: str,
) -> bool:
    """Check that setting proposed_parent_id won't create a cycle.

    Walks up from proposed_parent_id through packages to root. If we encounter
    diagram_id, it would create a cycle. Returns True if safe, False if cycle
    detected. Checks both packages and diagrams tables since parents are packages.
    """
    if diagram_id == proposed_parent_id:
        return False

    current = proposed_parent_id
    visited: set[str] = set()
    while current is not None:
        if current == diagram_id:
            return False
        if current in visited:
            return False  # existing cycle in data -- shouldn't happen
        visited.add(current)
        # Check packages table first (parent chain goes through packages)
        cursor = await db.execute(
            "SELECT parent_package_id FROM packages WHERE id = ? AND is_deleted = 0",
            (current,),
        )
        row = await cursor.fetchone()
        if row is None:
            # Also check diagrams table in case of mixed hierarchy
            cursor = await db.execute(
                "SELECT parent_package_id FROM diagrams WHERE id = ? AND is_deleted = 0",
                (current,),
            )
            row = await cursor.fetchone()
            if row is None:
                break
        current = row[0]
    return True


async def set_diagram_parent(
    db: aiosqlite.Connection,
    diagram_id: str,
    parent_package_id: str | None,
    updated_by: str,
) -> dict[str, object] | None:
    """Set or unset a diagram's parent package. Returns None on failure."""
    # Verify diagram exists
    cursor = await db.execute(
        "SELECT id FROM diagrams WHERE id = ? AND is_deleted = 0",
        (diagram_id,),
    )
    if await cursor.fetchone() is None:
        return None

    # If setting a parent, verify parent package exists and no cycle
    if parent_package_id is not None:
        cursor = await db.execute(
            "SELECT id FROM packages WHERE id = ? AND is_deleted = 0",
            (parent_package_id,),
        )
        if await cursor.fetchone() is None:
            return None

        if not await validate_no_cycle(db, diagram_id, parent_package_id):
            return {"error": "cycle"}

    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "UPDATE diagrams SET parent_package_id = ?, updated_at = ? WHERE id = ?",
        (parent_package_id, now, diagram_id),
    )
    await db.commit()
    return {"diagram_id": diagram_id, "parent_package_id": parent_package_id}


async def get_diagram_ancestors(
    db: aiosqlite.Connection,
    diagram_id: str,
) -> list[dict[str, object]]:
    """Get ancestor chain from diagram to root (breadcrumb order: root first).

    Since diagram parents are packages, the ancestor chain walks through the
    packages table.
    """
    ancestors: list[dict[str, object]] = []
    current = diagram_id

    # First get the parent of the starting diagram
    cursor = await db.execute(
        "SELECT parent_package_id FROM diagrams WHERE id = ? AND is_deleted = 0",
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
        # Query packages table for ancestors (parent chain goes through packages)
        cursor = await db.execute(
            "SELECT p.id, pv.name, p.parent_package_id "
            "FROM packages p "
            "JOIN package_versions pv ON p.id = pv.package_id "
            "AND p.current_version = pv.version "
            "WHERE p.id = ? AND p.is_deleted = 0",
            (current,),
        )
        row = await cursor.fetchone()
        if row is None:
            break
        ancestors.append({
            "id": row[0],
            "name": row[1],
            "type": "package",
            "parent_package_id": row[2],
        })
        current = row[2]

    ancestors.reverse()  # root first
    return ancestors


async def get_diagram_children(
    db: aiosqlite.Connection,
    diagram_id: str,
) -> list[dict[str, object]]:
    """Get direct child diagrams of a diagram/package."""
    cursor = await db.execute(
        "SELECT d.id, dv.name, d.diagram_type, d.parent_package_id "
        "FROM diagrams d "
        "JOIN diagram_versions dv ON d.id = dv.diagram_id "
        "AND d.current_version = dv.version "
        "WHERE d.parent_package_id = ? AND d.is_deleted = 0 "
        "ORDER BY dv.name",
        (diagram_id,),
    )
    rows = await cursor.fetchall()
    return [
        {
            "id": r[0],
            "name": r[1],
            "diagram_type": r[2],
            "parent_package_id": r[3],
        }
        for r in rows
    ]


async def get_diagram_hierarchy(
    db: aiosqlite.Connection,
    root_id: str | None = None,
    set_id: str | None = None,
) -> list[dict[str, object]]:
    """Get the diagram hierarchy as a tree.

    Builds a combined tree of packages and diagrams.  Packages act as
    folder nodes (node_type="package") and diagrams as leaf/content nodes
    (node_type="diagram").  Each diagram's parent_package_id points to a
    package, and packages can nest via their own parent_package_id.

    If root_id is given, returns subtree rooted at that node.
    If set_id is given, only includes items from that set.
    Otherwise returns all root nodes with their children.
    """
    params: list[str] = []
    pkg_set_filter = ""
    diag_set_filter = ""
    if set_id is not None:
        pkg_set_filter = "AND p.set_id = ? "
        diag_set_filter = "AND d.set_id = ? "
        params = [set_id, set_id]

    # Fetch packages and diagrams in a single UNION query so we can
    # build the full hierarchy in one pass.
    query = (
        "SELECT t.id, t.name, t.node_type, t.parent_package_id, t.diagram_type, t.data, t.notation "
        "FROM ("
        "  SELECT p.id, pv.name, 'package' AS node_type, p.parent_package_id, "
        "         NULL AS diagram_type, NULL AS data, NULL AS notation "
        "  FROM packages p "
        "  JOIN package_versions pv ON p.id = pv.package_id "
        "       AND p.current_version = pv.version "
        f"  WHERE p.is_deleted = 0 {pkg_set_filter}"
        "  UNION ALL "
        "  SELECT d.id, dv.name, 'diagram' AS node_type, d.parent_package_id, "
        "         d.diagram_type, dv.data, d.notation "
        "  FROM diagrams d "
        "  JOIN diagram_versions dv ON d.id = dv.diagram_id "
        "       AND d.current_version = dv.version "
        f"  WHERE d.is_deleted = 0 {diag_set_filter}"
        ") t "
        "ORDER BY t.node_type, t.name"
    )
    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()

    # Build lookup structures
    nodes: dict[str, dict[str, object]] = {}
    for r in rows:
        node_type = r[2]
        has_content = False
        if node_type == "diagram":
            try:
                data = json.loads(r[5]) if r[5] else {}
                if isinstance(data, dict):
                    has_content = bool(data.get("nodes")) or bool(
                        data.get("participants")
                    )
            except (json.JSONDecodeError, TypeError):
                pass
        nodes[r[0]] = {
            "id": r[0],
            "name": r[1],
            "node_type": node_type,
            "diagram_type": r[4],
            "notation": r[6],
            "parent_package_id": r[3],
            "has_content": has_content,
            "children": [],
        }

    # Build tree — parent_package_id references are now resolvable
    # because both packages and diagrams are in the nodes dict.
    roots: list[dict[str, object]] = []
    for node in nodes.values():
        parent_id = node["parent_package_id"]
        if parent_id is not None and parent_id in nodes:
            parent_children: list[dict[str, object]] = nodes[parent_id]["children"]  # type: ignore[assignment]
            parent_children.append(node)
        else:
            roots.append(node)

    if root_id is not None:
        # Return subtree rooted at root_id
        if root_id in nodes:
            return [nodes[root_id]]
        return []

    return roots


async def get_diagram_versions(
    db: aiosqlite.Connection,
    diagram_id: str,
) -> list[dict[str, object]]:
    """Get all versions of a diagram."""
    cursor = await db.execute(
        "SELECT dv.diagram_id, dv.version, dv.name, dv.description, dv.data, "
        "dv.change_type, dv.change_summary, dv.rollback_to, "
        "dv.created_at, dv.created_by, "
        "u.username, dv.metadata "
        "FROM diagram_versions dv "
        "LEFT JOIN users u ON dv.created_by = u.id "
        "WHERE dv.diagram_id = ? "
        "ORDER BY dv.version DESC",
        (diagram_id,),
    )
    rows = await cursor.fetchall()
    return [
        {
            "diagram_id": r[0],
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


async def rollback_diagram(
    db: aiosqlite.Connection,
    diagram_id: str,
    *,
    target_version: int,
    rolled_back_by: str,
    expected_version: int,
) -> dict[str, object] | None:
    """Rollback diagram to a previous version (creates new version). Returns None on conflict."""
    # Check current version (OCC)
    cursor = await db.execute(
        "SELECT current_version FROM diagrams WHERE id = ? AND is_deleted = 0",
        (diagram_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    current_version: int = row[0]
    if current_version != expected_version:
        return None

    # Get target version data
    cursor = await db.execute(
        "SELECT name, description, data, metadata FROM diagram_versions "
        "WHERE diagram_id = ? AND version = ?",
        (diagram_id, target_version),
    )
    target_row = await cursor.fetchone()
    if target_row is None:
        return None

    new_version = current_version + 1
    now = datetime.now(tz=UTC).isoformat()

    await db.execute(
        "UPDATE diagrams SET current_version = ?, updated_at = ? WHERE id = ?",
        (new_version, now, diagram_id),
    )
    await db.execute(
        "INSERT INTO diagram_versions (diagram_id, version, name, description, "
        "data, metadata, change_type, rollback_to, created_at, created_by) "
        "VALUES (?, ?, ?, ?, ?, ?, 'rollback', ?, ?, ?)",
        (diagram_id, new_version, target_row[0], target_row[1],
         target_row[2], target_row[3], target_version, now, rolled_back_by),
    )
    await db.commit()

    return await get_diagram(db, diagram_id)
