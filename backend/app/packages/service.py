"""Package CRUD service with versioning."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.migrations.m012_sets import DEFAULT_SET_ID

if TYPE_CHECKING:
    import aiosqlite


async def create_package(
    db: aiosqlite.Connection,
    *,
    name: str,
    description: str | None,
    created_by: str,
    parent_package_id: str | None = None,
    set_id: str | None = None,
    metadata: dict[str, object] | None = None,
    change_summary: str | None = None,
) -> dict[str, object]:
    """Create a new package with initial version."""
    package_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    metadata_json = json.dumps(metadata) if metadata else None
    effective_set_id = set_id or DEFAULT_SET_ID

    await db.execute(
        "INSERT INTO packages (id, current_version, "
        "created_at, created_by, updated_at, parent_package_id, set_id) "
        "VALUES (?, 1, ?, ?, ?, ?, ?)",
        (package_id, now, created_by, now, parent_package_id, effective_set_id),
    )
    await db.execute(
        "INSERT INTO package_versions (package_id, version, name, description, "
        "data, change_type, change_summary, created_at, created_by, metadata) "
        "VALUES (?, 1, ?, ?, '{}', 'create', ?, ?, ?, ?)",
        (package_id, name, description, change_summary, now, created_by, metadata_json),
    )
    await db.commit()

    return {
        "id": package_id,
        "current_version": 1,
        "name": name,
        "description": description,
        "created_at": now,
        "created_by": created_by,
        "updated_at": now,
        "is_deleted": False,
        "parent_package_id": parent_package_id,
        "set_id": effective_set_id,
        "metadata": metadata,
    }


async def get_package(
    db: aiosqlite.Connection,
    package_id: str,
) -> dict[str, object] | None:
    """Get a package with its current version data."""
    cursor = await db.execute(
        "SELECT p.id, p.current_version, "
        "pv.name, pv.description, "
        "p.created_at, p.created_by, p.updated_at, p.is_deleted, "
        "u.username, p.parent_package_id, p.set_id, s.name, pv.metadata "
        "FROM packages p "
        "JOIN package_versions pv ON p.id = pv.package_id "
        "AND p.current_version = pv.version "
        "LEFT JOIN users u ON p.created_by = u.id "
        "LEFT JOIN sets s ON p.set_id = s.id "
        "WHERE p.id = ? AND p.is_deleted = 0",
        (package_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    return {
        "id": row[0],
        "current_version": row[1],
        "name": row[2],
        "description": row[3],
        "created_at": row[4],
        "created_by": row[5],
        "updated_at": row[6],
        "is_deleted": bool(row[7]),
        "created_by_username": row[8] or "Unknown",
        "parent_package_id": row[9],
        "set_id": row[10],
        "set_name": row[11],
        "metadata": json.loads(row[12]) if row[12] else None,
    }


async def list_packages(
    db: aiosqlite.Connection,
    *,
    set_id: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict[str, object]], int]:
    """List packages with pagination."""
    where_clauses = ["p.is_deleted = 0"]
    params: list[object] = []

    if set_id:
        where_clauses.append("p.set_id = ?")
        params.append(set_id)

    where_sql = " AND ".join(where_clauses)

    cursor = await db.execute(
        f"SELECT COUNT(*) FROM packages p WHERE {where_sql}",  # noqa: S608
        params,
    )
    count_row = await cursor.fetchone()
    total: int = count_row[0]  # type: ignore[index]

    offset = (page - 1) * page_size
    cursor = await db.execute(
        f"SELECT p.id, p.current_version, "  # noqa: S608
        "pv.name, pv.description, "
        "p.created_at, p.created_by, p.updated_at, p.is_deleted, "
        "p.parent_package_id, p.set_id, s.name, pv.metadata "
        "FROM packages p "
        "JOIN package_versions pv ON p.id = pv.package_id "
        "AND p.current_version = pv.version "
        "LEFT JOIN sets s ON p.set_id = s.id "
        f"WHERE {where_sql} "
        "ORDER BY p.updated_at DESC LIMIT ? OFFSET ?",
        [*params, page_size, offset],
    )
    rows = await cursor.fetchall()

    items = [
        {
            "id": r[0],
            "current_version": r[1],
            "name": r[2],
            "description": r[3],
            "created_at": r[4],
            "created_by": r[5],
            "updated_at": r[6],
            "is_deleted": bool(r[7]),
            "parent_package_id": r[8],
            "set_id": r[9],
            "set_name": r[10],
            "metadata": json.loads(r[11]) if r[11] else None,
        }
        for r in rows
    ]
    return items, total


async def update_package(
    db: aiosqlite.Connection,
    package_id: str,
    *,
    name: str,
    description: str | None,
    change_summary: str | None,
    updated_by: str,
    expected_version: int,
    metadata: dict[str, object] | None = None,
) -> dict[str, object] | None:
    """Update a package with OCC."""
    cursor = await db.execute(
        "SELECT current_version FROM packages WHERE id = ? AND is_deleted = 0",
        (package_id,),
    )
    row = await cursor.fetchone()
    if row is None or row[0] != expected_version:
        return None

    new_version = row[0] + 1
    now = datetime.now(tz=UTC).isoformat()
    metadata_json = json.dumps(metadata) if metadata else None

    await db.execute(
        "UPDATE packages SET current_version = ?, updated_at = ? WHERE id = ?",
        (new_version, now, package_id),
    )
    await db.execute(
        "INSERT INTO package_versions (package_id, version, name, description, "
        "data, change_type, change_summary, created_at, created_by, metadata) "
        "VALUES (?, ?, ?, ?, '{}', 'update', ?, ?, ?, ?)",
        (package_id, new_version, name, description,
         change_summary, now, updated_by, metadata_json),
    )
    await db.commit()

    return {"current_version": new_version, "updated_at": now}


async def soft_delete_package(
    db: aiosqlite.Connection,
    package_id: str,
    *,
    deleted_by: str,
    expected_version: int,
) -> bool:
    """Soft-delete a package."""
    cursor = await db.execute(
        "SELECT current_version FROM packages WHERE id = ? AND is_deleted = 0",
        (package_id,),
    )
    row = await cursor.fetchone()
    if row is None or row[0] != expected_version:
        return False

    new_version = row[0] + 1
    now = datetime.now(tz=UTC).isoformat()

    cursor = await db.execute(
        "SELECT name, description FROM package_versions "
        "WHERE package_id = ? AND version = ?",
        (package_id, row[0]),
    )
    ver_row = await cursor.fetchone()

    await db.execute(
        "UPDATE packages SET current_version = ?, updated_at = ?, "
        "is_deleted = 1 WHERE id = ?",
        (new_version, now, package_id),
    )
    await db.execute(
        "INSERT INTO package_versions (package_id, version, name, description, "
        "data, change_type, created_at, created_by) "
        "VALUES (?, ?, ?, ?, '{}', 'delete', ?, ?)",
        (package_id, new_version, ver_row[0], ver_row[1], now, deleted_by),
    )
    await db.commit()
    return True


async def validate_no_cycle(
    db: aiosqlite.Connection,
    package_id: str,
    proposed_parent_id: str,
) -> bool:
    """Check that setting proposed_parent_id won't create a cycle.

    Walks up from proposed_parent_id to root. If we encounter package_id,
    it would create a cycle. Returns True if safe, False if cycle detected.
    """
    if package_id == proposed_parent_id:
        return False

    current = proposed_parent_id
    visited: set[str] = set()
    while current is not None:
        if current == package_id:
            return False
        if current in visited:
            return False  # existing cycle in data -- shouldn't happen
        visited.add(current)
        cursor = await db.execute(
            "SELECT parent_package_id FROM packages WHERE id = ? AND is_deleted = 0",
            (current,),
        )
        row = await cursor.fetchone()
        if row is None:
            break
        current = row[0]
    return True


async def set_package_parent(
    db: aiosqlite.Connection,
    package_id: str,
    parent_package_id: str | None,
    updated_by: str,
) -> dict[str, object] | None:
    """Set or unset a package's parent. Returns None on failure."""
    # Verify package exists
    cursor = await db.execute(
        "SELECT id FROM packages WHERE id = ? AND is_deleted = 0",
        (package_id,),
    )
    if await cursor.fetchone() is None:
        return None

    # If setting a parent, verify parent exists and no cycle
    if parent_package_id is not None:
        cursor = await db.execute(
            "SELECT id FROM packages WHERE id = ? AND is_deleted = 0",
            (parent_package_id,),
        )
        if await cursor.fetchone() is None:
            return None

        if not await validate_no_cycle(db, package_id, parent_package_id):
            return {"error": "cycle"}

    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "UPDATE packages SET parent_package_id = ?, updated_at = ? WHERE id = ?",
        (parent_package_id, now, package_id),
    )
    await db.commit()
    return {"package_id": package_id, "parent_package_id": parent_package_id}


async def get_package_ancestors(
    db: aiosqlite.Connection,
    package_id: str,
) -> list[dict[str, object]]:
    """Get ancestor chain from package to root (breadcrumb order: root first)."""
    ancestors: list[dict[str, object]] = []
    current = package_id

    # First get the parent of the starting package
    cursor = await db.execute(
        "SELECT parent_package_id FROM packages WHERE id = ? AND is_deleted = 0",
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
            "parent_package_id": row[2],
        })
        current = row[2]

    ancestors.reverse()  # root first
    return ancestors


async def get_package_children(
    db: aiosqlite.Connection,
    package_id: str,
) -> list[dict[str, object]]:
    """Get direct children of a package."""
    cursor = await db.execute(
        "SELECT p.id, pv.name, p.parent_package_id "
        "FROM packages p "
        "JOIN package_versions pv ON p.id = pv.package_id "
        "AND p.current_version = pv.version "
        "WHERE p.parent_package_id = ? AND p.is_deleted = 0 "
        "ORDER BY pv.name",
        (package_id,),
    )
    rows = await cursor.fetchall()
    return [
        {
            "id": r[0],
            "name": r[1],
            "parent_package_id": r[2],
        }
        for r in rows
    ]


async def get_package_hierarchy(
    db: aiosqlite.Connection,
    root_id: str | None = None,
    set_id: str | None = None,
) -> list[dict[str, object]]:
    """Get the package hierarchy as a tree.

    If root_id is given, returns subtree rooted at that package.
    If set_id is given, only includes packages from that set.
    Otherwise returns all root packages with their children.
    """
    # Fetch all non-deleted packages (optionally filtered by set)
    query = (
        "SELECT p.id, pv.name, p.parent_package_id "
        "FROM packages p "
        "JOIN package_versions pv ON p.id = pv.package_id "
        "AND p.current_version = pv.version "
        "WHERE p.is_deleted = 0 "
    )
    params: list[str] = []
    if set_id is not None:
        query += "AND p.set_id = ? "
        params.append(set_id)
    query += "ORDER BY pv.name"
    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()

    # Build lookup structures
    nodes: dict[str, dict[str, object]] = {}
    for r in rows:
        nodes[r[0]] = {
            "id": r[0],
            "name": r[1],
            "parent_package_id": r[2],
            "children": [],
        }

    # Build tree
    roots: list[dict[str, object]] = []
    for node in nodes.values():
        parent_id = node["parent_package_id"]
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


async def count_package_descendants(
    db: aiosqlite.Connection,
    package_id: str,
) -> dict[str, int]:
    """Count all descendant packages and diagrams under a package (non-deleted only)."""
    # Recursive CTE to find all descendant package IDs
    cursor = await db.execute(
        "WITH RECURSIVE descendants(id) AS ("
        "  SELECT id FROM packages "
        "  WHERE parent_package_id = ? AND is_deleted = 0 "
        "  UNION ALL "
        "  SELECT p.id FROM packages p "
        "  JOIN descendants d ON p.parent_package_id = d.id "
        "  WHERE p.is_deleted = 0"
        ") SELECT id FROM descendants",
        (package_id,),
    )
    child_package_ids = [row[0] for row in await cursor.fetchall()]

    # Count diagrams under the root and all descendant packages
    all_package_ids = [package_id, *child_package_ids]
    placeholders = ",".join("?" for _ in all_package_ids)
    cursor = await db.execute(
        f"SELECT COUNT(*) FROM diagrams "  # noqa: S608
        f"WHERE parent_package_id IN ({placeholders}) AND is_deleted = 0",
        all_package_ids,
    )
    diagram_count = (await cursor.fetchone())[0]

    return {"child_packages": len(child_package_ids), "child_diagrams": diagram_count}


async def cascade_delete_package(
    db: aiosqlite.Connection,
    package_id: str,
    *,
    deleted_by: str,
    expected_version: int,
) -> bool:
    """Cascade soft-delete a package and all descendants."""
    # OCC check on root package
    cursor = await db.execute(
        "SELECT current_version FROM packages WHERE id = ? AND is_deleted = 0",
        (package_id,),
    )
    row = await cursor.fetchone()
    if row is None or row[0] != expected_version:
        return False

    deleted_group_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()

    # Collect all descendant package IDs via recursive CTE
    cursor = await db.execute(
        "WITH RECURSIVE descendants(id) AS ("
        "  SELECT id FROM packages "
        "  WHERE parent_package_id = ? AND is_deleted = 0 "
        "  UNION ALL "
        "  SELECT p.id FROM packages p "
        "  JOIN descendants d ON p.parent_package_id = d.id "
        "  WHERE p.is_deleted = 0"
        ") SELECT id FROM descendants",
        (package_id,),
    )
    child_package_ids = [row[0] for row in await cursor.fetchall()]

    # All packages to delete: root + descendants
    all_package_ids = [package_id, *child_package_ids]

    # Soft-delete each package
    for pid in all_package_ids:
        cursor = await db.execute(
            "SELECT current_version FROM packages WHERE id = ? AND is_deleted = 0",
            (pid,),
        )
        pkg_row = await cursor.fetchone()
        if pkg_row is None:
            continue
        new_version = pkg_row[0] + 1

        cursor = await db.execute(
            "SELECT name, description FROM package_versions "
            "WHERE package_id = ? AND version = ?",
            (pid, pkg_row[0]),
        )
        ver_row = await cursor.fetchone()

        await db.execute(
            "UPDATE packages SET current_version = ?, updated_at = ?, "
            "is_deleted = 1, deleted_group_id = ? WHERE id = ?",
            (new_version, now, deleted_group_id, pid),
        )
        await db.execute(
            "INSERT INTO package_versions (package_id, version, name, description, "
            "data, change_type, created_at, created_by) "
            "VALUES (?, ?, ?, ?, '{}', 'delete', ?, ?)",
            (pid, new_version, ver_row[0], ver_row[1], now, deleted_by),
        )

    # Soft-delete all diagrams under any of those packages
    placeholders = ",".join("?" for _ in all_package_ids)
    cursor = await db.execute(
        f"SELECT id, current_version FROM diagrams "  # noqa: S608
        f"WHERE parent_package_id IN ({placeholders}) AND is_deleted = 0",
        all_package_ids,
    )
    diagram_rows = await cursor.fetchall()

    for did, d_version in diagram_rows:
        new_d_version = d_version + 1
        cursor = await db.execute(
            "SELECT name, description, data FROM diagram_versions "
            "WHERE diagram_id = ? AND version = ?",
            (did, d_version),
        )
        d_ver_row = await cursor.fetchone()

        await db.execute(
            "UPDATE diagrams SET current_version = ?, updated_at = ?, "
            "is_deleted = 1, deleted_group_id = ? WHERE id = ?",
            (new_d_version, now, deleted_group_id, did),
        )
        await db.execute(
            "INSERT INTO diagram_versions (diagram_id, version, name, description, "
            "data, change_type, created_at, created_by) "
            "VALUES (?, ?, ?, ?, ?, 'delete', ?, ?)",
            (did, new_d_version, d_ver_row[0], d_ver_row[1],
             d_ver_row[2], now, deleted_by),
        )

    await db.commit()

    # Remove deleted diagrams from search index
    from app.search.service import remove_diagram_index as _remove_diagram_index

    for did, _ in diagram_rows:
        await _remove_diagram_index(db, did)
    await db.commit()

    return True


async def restore_package(
    db: aiosqlite.Connection,
    package_id: str,
    *,
    restored_by: str,
) -> bool:
    """Restore a soft-deleted package."""
    cursor = await db.execute(
        "SELECT current_version FROM packages WHERE id = ? AND is_deleted = 1",
        (package_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return False

    new_version = row[0] + 1
    now = datetime.now(tz=UTC).isoformat()

    cursor = await db.execute(
        "SELECT name, description FROM package_versions "
        "WHERE package_id = ? AND version = ?",
        (package_id, row[0]),
    )
    ver_row = await cursor.fetchone()

    await db.execute(
        "UPDATE packages SET current_version = ?, updated_at = ?, "
        "is_deleted = 0, deleted_group_id = NULL WHERE id = ?",
        (new_version, now, package_id),
    )
    await db.execute(
        "INSERT INTO package_versions (package_id, version, name, description, "
        "data, change_type, created_at, created_by) "
        "VALUES (?, ?, ?, ?, '{}', 'restore', ?, ?)",
        (package_id, new_version, ver_row[0], ver_row[1], now, restored_by),
    )
    await db.commit()
    return True


async def get_package_versions(
    db: aiosqlite.Connection,
    package_id: str,
) -> list[dict[str, object]]:
    """Get all versions of a package."""
    cursor = await db.execute(
        "SELECT pv.package_id, pv.version, pv.name, pv.description, pv.data, "
        "pv.change_type, pv.change_summary, "
        "pv.created_at, pv.created_by, "
        "u.username, pv.metadata "
        "FROM package_versions pv "
        "LEFT JOIN users u ON pv.created_by = u.id "
        "WHERE pv.package_id = ? "
        "ORDER BY pv.version DESC",
        (package_id,),
    )
    rows = await cursor.fetchall()
    return [
        {
            "package_id": r[0],
            "version": r[1],
            "name": r[2],
            "description": r[3],
            "data": json.loads(r[4]) if r[4] else {},
            "change_type": r[5],
            "change_summary": r[6],
            "created_at": r[7],
            "created_by": r[8],
            "created_by_username": r[9] or "Unknown",
            "metadata": json.loads(r[10]) if r[10] else None,
        }
        for r in rows
    ]
