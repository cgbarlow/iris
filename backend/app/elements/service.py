"""Element CRUD service with versioning per SPEC-006-A."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.common.nullable_filter import parse_nullable_id
from app.migrations.m012_sets import DEFAULT_SET_ID
from app.search.service import index_element as _index_element
from app.search.service import remove_element_index as _remove_element_index

if TYPE_CHECKING:
    import aiosqlite
    from app.db.adapter import DatabasePort


class ElementPackageInvariantError(ValueError):
    """Raised when (element.set_id, package.set_id) are inconsistent.

    The router translates this into HTTP 422 with the message intact.
    See ADR-184 for the invariant statement.
    """


class ElementDetailDiagramError(ValueError):
    """Raised when an element's detail_diagram_id points at a diagram
    that does not exist or is soft-deleted (ADR-221).

    The router translates this into HTTP 422 with the message intact.
    Cross-set targets are allowed — only existence is checked.
    """


class ElementParentInvariantError(ValueError):
    """Raised when an element's parent_element_id is invalid — missing,
    soft-deleted, cross-set, a containment cycle, or self-parent (ADR-231).

    The router translates this into HTTP 422 with the message intact.
    """


async def _validate_detail_diagram_exists(
    db: DatabasePort,
    detail_diagram_id: str | None,
) -> None:
    """Ensure ``detail_diagram_id`` references a live diagram (ADR-221).

    ``None`` (clear / unset) is always valid. A non-null id must resolve
    to a non-deleted ``diagrams`` row, else
    :class:`ElementDetailDiagramError`. No set constraint — cross-set
    drill links are intentionally allowed.
    """
    if detail_diagram_id is None:
        return
    cursor = await db.execute(
        "SELECT 1 FROM diagrams WHERE id = ? AND is_deleted = 0",
        (detail_diagram_id,),
    )
    if await cursor.fetchone() is None:
        msg = f"Detail diagram {detail_diagram_id} not found"
        raise ElementDetailDiagramError(msg)


async def _validate_element_package_set_consistency(
    db: DatabasePort,
    *,
    set_id: str | None,
    package_id: str | None,
) -> None:
    """Enforce the (element.set_id, package.set_id) invariant.

    Allowed states:
      - package_id is None: no constraint.
      - set_id is None: no constraint.
      - package's set_id is None: package belongs to no set; any
        element set is fine.
      - package's set_id == element's set_id: match.

    Any other combination raises :class:`ElementPackageInvariantError`.
    """
    if package_id is None or set_id is None:
        return
    cursor = await db.execute(
        "SELECT set_id FROM packages WHERE id = ? AND is_deleted = 0",
        (package_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        msg = f"Package {package_id} not found"
        raise ElementPackageInvariantError(msg)
    pkg_set_id = row[0]
    if pkg_set_id is not None and pkg_set_id != set_id:
        msg = (
            f"Element belongs to set {set_id} but package {package_id} "
            f"belongs to set {pkg_set_id}"
        )
        raise ElementPackageInvariantError(msg)


async def _validate_parent_element(
    db: DatabasePort,
    *,
    parent_element_id: str | None,
    set_id: str | None,
    element_id: str | None = None,
) -> None:
    """Ensure ``parent_element_id`` is a live element in the same set, and
    (on update) that linking it forms no cycle or self-parent (ADR-231).

    ``None`` (clear / unset) is always valid. Element containment is
    single-set — unlike the cross-set ADR-221 detail link.
    """
    if parent_element_id is None:
        return
    if element_id is not None and parent_element_id == element_id:
        msg = "An element cannot be its own parent"
        raise ElementParentInvariantError(msg)
    cursor = await db.execute(
        "SELECT set_id FROM elements WHERE id = ? AND is_deleted = 0",
        (parent_element_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        msg = f"Parent element {parent_element_id} not found"
        raise ElementParentInvariantError(msg)
    parent_set_id = row[0]
    if set_id is not None and parent_set_id is not None and parent_set_id != set_id:
        msg = (
            f"Element belongs to set {set_id} but parent element "
            f"{parent_element_id} belongs to set {parent_set_id}"
        )
        raise ElementParentInvariantError(msg)
    if element_id is not None:
        await _validate_no_element_cycle(db, element_id, parent_element_id)


async def _validate_no_element_cycle(
    db: DatabasePort,
    element_id: str,
    proposed_parent_id: str,
) -> None:
    """Walk up the proposed parent's ancestry; reject if it reaches
    ``element_id`` (a cycle). Mirrors ``packages.service.validate_no_cycle``.
    """
    seen: set[str] = set()
    current: str | None = proposed_parent_id
    while current is not None:
        if current == element_id:
            msg = "Cannot set parent: would create a containment cycle"
            raise ElementParentInvariantError(msg)
        if current in seen:
            break  # pre-existing cycle elsewhere — bail rather than loop
        seen.add(current)
        cursor = await db.execute(
            "SELECT parent_element_id FROM elements WHERE id = ? AND is_deleted = 0",
            (current,),
        )
        r = await cursor.fetchone()
        current = r[0] if r else None


async def create_element(
    db: DatabasePort,
    *,
    element_type: str,
    name: str,
    description: str | None,
    data: dict[str, object],
    created_by: str,
    set_id: str | None = None,
    package_id: str | None = None,
    detail_diagram_id: str | None = None,
    parent_element_id: str | None = None,
    metadata: dict[str, object] | None = None,
    change_summary: str | None = None,
    notation: str = "simple",
) -> dict[str, object]:
    """Create a new element with initial version."""
    element_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    data_json = json.dumps(data)
    metadata_json = json.dumps(metadata) if metadata else None
    effective_set_id = set_id or DEFAULT_SET_ID

    await _validate_element_package_set_consistency(
        db, set_id=effective_set_id, package_id=package_id,
    )
    await _validate_detail_diagram_exists(db, detail_diagram_id)
    # No cycle check at create — a brand-new id can't be an ancestor (ADR-231).
    await _validate_parent_element(
        db, parent_element_id=parent_element_id, set_id=effective_set_id,
    )

    await db.execute(
        "INSERT INTO elements (id, element_type, current_version, "
        "created_at, created_by, updated_at, set_id, package_id, "
        "detail_diagram_id, parent_element_id, notation) "
        "VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?)",
        (element_id, element_type, now, created_by, now,
         effective_set_id, package_id, detail_diagram_id, parent_element_id, notation),
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
        "package_id": package_id,
        "detail_diagram_id": detail_diagram_id,
        "parent_element_id": parent_element_id,
        "metadata": metadata,
        "notation": notation,
    }


async def get_element(
    db: DatabasePort,
    element_id: str,
) -> dict[str, object] | None:
    """Get an element with its current version data."""
    cursor = await db.execute(
        "SELECT e.id, e.element_type, e.current_version, "
        "ev.name, ev.description, ev.data, "
        "e.created_at, e.created_by, e.updated_at, e.is_deleted, "
        "u.username, e.set_id, s.name, ev.metadata, e.notation, "
        "e.package_id, e.detail_diagram_id, e.parent_element_id, "
        "(SELECT pv.name FROM packages p "
        "  JOIN package_versions pv ON p.id = pv.package_id "
        "    AND p.current_version = pv.version "
        "  WHERE p.id = e.package_id) AS package_name, "
        "(SELECT pev.name FROM elements pe "
        "  JOIN element_versions pev ON pe.id = pev.element_id "
        "    AND pe.current_version = pev.version "
        "  WHERE pe.id = e.parent_element_id) AS parent_element_name "
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
        "notation": row[14] or "simple",
        "package_id": row[15],
        "detail_diagram_id": row[16],
        "parent_element_id": row[17],
        "package_name": row[18],
        "parent_element_name": row[19],
    }

    # Enrich with tags
    tag_cursor = await db.execute(
        "SELECT tag FROM element_tags WHERE element_id = ? ORDER BY tag",
        (element_id,),
    )
    tag_rows = await tag_cursor.fetchall()
    element["tags"] = [r[0] for r in tag_rows]

    # Relationship count
    rel_cursor = await db.execute(
        "SELECT COUNT(*) FROM relationships "
        "WHERE (source_element_id = ? OR target_element_id = ?) AND is_deleted = 0",
        (element_id, element_id),
    )
    rel_row = await rel_cursor.fetchone()
    element["relationship_count"] = rel_row[0] if rel_row else 0

    # Diagram usage count
    diagram_cursor = await db.execute(
        "SELECT COUNT(DISTINCT d.id) FROM diagrams d "
        "JOIN diagram_versions dv ON d.id = dv.diagram_id AND d.current_version = dv.version "
        "WHERE d.is_deleted = 0 AND dv.data LIKE ?",
        (f'%{element_id}%',),
    )
    diagram_row = await diagram_cursor.fetchone()
    element["diagram_usage_count"] = diagram_row[0] if diagram_row else 0

    return element


async def list_elements(
    db: DatabasePort,
    *,
    element_type: str | None = None,
    set_id: str | None = None,
    collection_id: str | None = None,
    package_id: str | None = None,
    notation: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict[str, object]], int]:
    """List elements with pagination. Returns (items, total_count).

    ``package_id`` has three-valued semantics (ADR-185):
    omitted = no filter; literal ``"null"`` = ``package_id IS NULL``;
    any other string = exact match.
    """
    where_clauses = ["e.is_deleted = 0"]
    params: list[object] = []

    if element_type:
        where_clauses.append("e.element_type = ?")
        params.append(element_type)

    if set_id:
        where_clauses.append("e.set_id = ?")
        params.append(set_id)
    elif collection_id:
        where_clauses.append("e.set_id IN (SELECT id FROM sets WHERE collection_id = ?)")
        params.append(collection_id)

    pkg_filter = parse_nullable_id(package_id)
    if pkg_filter[0] == "is_null":
        where_clauses.append("e.package_id IS NULL")
    elif pkg_filter[0] == "eq":
        where_clauses.append("e.package_id = ?")
        params.append(pkg_filter[1])

    if notation:
        where_clauses.append("e.notation = ?")
        params.append(notation)

    if search:
        where_clauses.append("(ev.name LIKE ? OR ev.description LIKE ?)")
        params.append(f"%{search}%")
        params.append(f"%{search}%")

    where_sql = " AND ".join(where_clauses)

    # Count (join element_versions for search filter)
    count_join = (
        " JOIN element_versions ev ON e.id = ev.element_id AND e.current_version = ev.version"
        if search else ""
    )
    cursor = await db.execute(
        f"SELECT COUNT(*) FROM elements e{count_join} WHERE {where_sql}",  # noqa: S608
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
        "e.set_id, s.name, ev.metadata, e.notation, "
        "e.package_id, e.detail_diagram_id, e.parent_element_id, "
        "(SELECT pv.name FROM packages p "
        "  JOIN package_versions pv ON p.id = pv.package_id "
        "    AND p.current_version = pv.version "
        "  WHERE p.id = e.package_id) AS package_name, "
        "(SELECT pev.name FROM elements pe "
        "  JOIN element_versions pev ON pe.id = pev.element_id "
        "    AND pe.current_version = pev.version "
        "  WHERE pe.id = e.parent_element_id) AS parent_element_name "
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
            "notation": r[13] or "simple",
            "package_id": r[14],
            "detail_diagram_id": r[15],
            "parent_element_id": r[16],
            "package_name": r[17],
            "parent_element_name": r[18],
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


async def get_element_children(
    db: DatabasePort,
    element_id: str,
) -> list[dict[str, object]]:
    """Direct child elements (ADR-231), name + type, alphabetical."""
    cursor = await db.execute(
        "SELECT e.id, ev.name, e.element_type FROM elements e "
        "JOIN element_versions ev ON e.id = ev.element_id "
        "  AND e.current_version = ev.version "
        "WHERE e.parent_element_id = ? AND e.is_deleted = 0 "
        "ORDER BY ev.name",
        (element_id,),
    )
    return [
        {"id": r[0], "name": r[1], "element_type": r[2]}
        for r in await cursor.fetchall()
    ]


async def get_element_ancestors(
    db: DatabasePort,
    element_id: str,
) -> list[dict[str, object]]:
    """Containment breadcrumb, root-first (ADR-231). Excludes the element
    itself; cycle-guarded."""
    chain: list[dict[str, object]] = []
    seen: set[str] = set()
    cursor = await db.execute(
        "SELECT parent_element_id FROM elements WHERE id = ? AND is_deleted = 0",
        (element_id,),
    )
    head = await cursor.fetchone()
    current = head[0] if head else None
    while current is not None and current not in seen:
        seen.add(current)
        c = await db.execute(
            "SELECT e.id, ev.name, e.element_type, e.parent_element_id FROM elements e "
            "JOIN element_versions ev ON e.id = ev.element_id "
            "  AND e.current_version = ev.version "
            "WHERE e.id = ? AND e.is_deleted = 0",
            (current,),
        )
        row = await c.fetchone()
        if row is None:
            break
        chain.append({"id": row[0], "name": row[1], "element_type": row[2]})
        current = row[3]
    chain.reverse()
    return chain


_UNSET_PACKAGE_ID: Any = object()
_UNSET_DETAIL_DIAGRAM_ID: Any = object()
_UNSET_PARENT_ELEMENT_ID: Any = object()


async def update_element(
    db: DatabasePort,
    element_id: str,
    *,
    name: str,
    description: str | None,
    data: dict[str, object],
    change_summary: str | None,
    updated_by: str,
    expected_version: int,
    metadata: dict[str, object] | None = None,
    package_id: Any = _UNSET_PACKAGE_ID,
    detail_diagram_id: Any = _UNSET_DETAIL_DIAGRAM_ID,
    parent_element_id: Any = _UNSET_PARENT_ELEMENT_ID,
) -> dict[str, object] | None:
    """Update an element with optimistic concurrency. Returns None on conflict.

    ``package_id`` and ``detail_diagram_id`` are tri-state. The sentinel
    means "do not touch the column"; an explicit ``None`` clears the
    column; a string sets it. The package/set invariant runs whenever
    ``package_id`` is being touched; ``detail_diagram_id`` is validated to
    reference a live diagram whenever it is being touched (ADR-221).
    """
    # Check current version (OCC)
    cursor = await db.execute(
        "SELECT current_version, set_id FROM elements WHERE id = ? AND is_deleted = 0",
        (element_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    current_version: int = row[0]
    current_set_id: str | None = row[1]
    if current_version != expected_version:
        return None

    if package_id is not _UNSET_PACKAGE_ID:
        await _validate_element_package_set_consistency(
            db, set_id=current_set_id, package_id=package_id,
        )
    if detail_diagram_id is not _UNSET_DETAIL_DIAGRAM_ID:
        await _validate_detail_diagram_exists(db, detail_diagram_id)
    if parent_element_id is not _UNSET_PARENT_ELEMENT_ID:
        await _validate_parent_element(
            db, parent_element_id=parent_element_id,
            set_id=current_set_id, element_id=element_id,
        )

    new_version = current_version + 1
    now = datetime.now(tz=UTC).isoformat()
    data_json = json.dumps(data)
    metadata_json = json.dumps(metadata) if metadata else None

    # Build the SET clause dynamically so package_id and detail_diagram_id
    # can each be touched (or left untouched) independently. All clause
    # fragments are literal column assignments — no user text in the SQL.
    set_clauses = ["current_version = ?", "updated_at = ?"]
    set_params: list[object] = [new_version, now]
    if package_id is not _UNSET_PACKAGE_ID:
        set_clauses.append("package_id = ?")
        set_params.append(package_id)
    if detail_diagram_id is not _UNSET_DETAIL_DIAGRAM_ID:
        set_clauses.append("detail_diagram_id = ?")
        set_params.append(detail_diagram_id)
    if parent_element_id is not _UNSET_PARENT_ELEMENT_ID:
        set_clauses.append("parent_element_id = ?")
        set_params.append(parent_element_id)
    set_params.append(element_id)
    await db.execute(
        f"UPDATE elements SET {', '.join(set_clauses)} WHERE id = ?",  # noqa: S608
        set_params,
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
    db: DatabasePort,
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
    db: DatabasePort,
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


async def restore_element(
    db: DatabasePort,
    element_id: str,
    *,
    restored_by: str,
) -> bool:
    """Restore a soft-deleted element."""
    cursor = await db.execute(
        "SELECT current_version, element_type FROM elements "
        "WHERE id = ? AND is_deleted = 1",
        (element_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return False

    new_version = row[0] + 1
    element_type = row[1]
    now = datetime.now(tz=UTC).isoformat()

    cursor = await db.execute(
        "SELECT name, description, data FROM element_versions "
        "WHERE element_id = ? AND version = ?",
        (element_id, row[0]),
    )
    ver_row = await cursor.fetchone()

    await db.execute(
        "UPDATE elements SET current_version = ?, updated_at = ?, "
        "is_deleted = 0, deleted_group_id = NULL WHERE id = ?",
        (new_version, now, element_id),
    )
    await db.execute(
        "INSERT INTO element_versions (element_id, version, name, description, "
        "data, change_type, created_at, created_by) "
        "VALUES (?, ?, ?, ?, ?, 'restore', ?, ?)",
        (element_id, new_version, ver_row[0], ver_row[1],
         ver_row[2], now, restored_by),
    )
    await db.commit()

    # Re-index for search
    await _index_element(
        db, element_id=element_id, name=ver_row[0],
        element_type=element_type, description=ver_row[1],
    )
    await db.commit()

    return True


async def cascade_delete_element(
    db: DatabasePort,
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
    db: DatabasePort,
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
    db: DatabasePort,
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
