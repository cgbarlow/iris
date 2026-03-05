"""Recycle bin service — list, restore, and permanently delete soft-deleted items."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.diagrams.service import restore_diagram
from app.elements.service import restore_element
from app.packages.service import restore_package

if TYPE_CHECKING:
    import aiosqlite


async def list_deleted_items(
    db: aiosqlite.Connection,
    *,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict[str, object]], int]:
    """List all soft-deleted items across packages, diagrams, and elements."""
    count_sql = (
        "SELECT ("
        "  SELECT COUNT(*) FROM packages WHERE is_deleted = 1"
        ") + ("
        "  SELECT COUNT(*) FROM diagrams WHERE is_deleted = 1"
        ") + ("
        "  SELECT COUNT(*) FROM elements WHERE is_deleted = 1"
        ")"
    )
    cursor = await db.execute(count_sql)
    total = (await cursor.fetchone())[0]

    offset = (page - 1) * page_size
    query = (
        "SELECT id, item_type, name, description, deleted_at, "
        "deleted_by_username, deleted_group_id, set_id, set_name, "
        "diagram_type, element_type "
        "FROM ("
        "  SELECT p.id, 'package' AS item_type, pv.name, pv.description, "
        "         p.updated_at AS deleted_at, u.username AS deleted_by_username, "
        "         p.deleted_group_id, p.set_id, s.name AS set_name, "
        "         NULL AS diagram_type, NULL AS element_type "
        "  FROM packages p "
        "  JOIN package_versions pv ON p.id = pv.package_id "
        "       AND p.current_version = pv.version "
        "  LEFT JOIN users u ON pv.created_by = u.id "
        "  LEFT JOIN sets s ON p.set_id = s.id "
        "  WHERE p.is_deleted = 1 "
        "  UNION ALL "
        "  SELECT d.id, 'diagram' AS item_type, dv.name, dv.description, "
        "         d.updated_at AS deleted_at, u.username AS deleted_by_username, "
        "         d.deleted_group_id, d.set_id, s.name AS set_name, "
        "         d.diagram_type, NULL AS element_type "
        "  FROM diagrams d "
        "  JOIN diagram_versions dv ON d.id = dv.diagram_id "
        "       AND d.current_version = dv.version "
        "  LEFT JOIN users u ON dv.created_by = u.id "
        "  LEFT JOIN sets s ON d.set_id = s.id "
        "  WHERE d.is_deleted = 1 "
        "  UNION ALL "
        "  SELECT e.id, 'element' AS item_type, ev.name, ev.description, "
        "         e.updated_at AS deleted_at, u.username AS deleted_by_username, "
        "         e.deleted_group_id, e.set_id, s.name AS set_name, "
        "         NULL AS diagram_type, e.element_type "
        "  FROM elements e "
        "  JOIN element_versions ev ON e.id = ev.element_id "
        "       AND e.current_version = ev.version "
        "  LEFT JOIN users u ON ev.created_by = u.id "
        "  LEFT JOIN sets s ON e.set_id = s.id "
        "  WHERE e.is_deleted = 1 "
        ") t "
        "ORDER BY deleted_at DESC "
        "LIMIT ? OFFSET ?"
    )
    cursor = await db.execute(query, (page_size, offset))
    rows = await cursor.fetchall()

    items = [
        {
            "id": r[0],
            "item_type": r[1],
            "name": r[2],
            "description": r[3],
            "deleted_at": r[4],
            "deleted_by_username": r[5],
            "deleted_group_id": r[6],
            "set_id": r[7],
            "set_name": r[8],
            "diagram_type": r[9],
            "element_type": r[10],
        }
        for r in rows
    ]
    return items, total


async def cascade_restore_by_group(
    db: aiosqlite.Connection,
    group_id: str,
    *,
    restored_by: str,
) -> int:
    """Restore all items sharing a deleted_group_id. Returns count restored."""
    count = 0

    # Restore packages first (parent-before-child order by walking hierarchy)
    cursor = await db.execute(
        "SELECT id FROM packages WHERE deleted_group_id = ? AND is_deleted = 1",
        (group_id,),
    )
    package_ids = [row[0] for row in await cursor.fetchall()]
    for pid in package_ids:
        if await restore_package(db, pid, restored_by=restored_by):
            count += 1

    # Restore diagrams
    cursor = await db.execute(
        "SELECT id FROM diagrams WHERE deleted_group_id = ? AND is_deleted = 1",
        (group_id,),
    )
    diagram_ids = [row[0] for row in await cursor.fetchall()]
    for did in diagram_ids:
        if await restore_diagram(db, did, restored_by=restored_by):
            count += 1

    # Restore elements
    cursor = await db.execute(
        "SELECT id FROM elements WHERE deleted_group_id = ? AND is_deleted = 1",
        (group_id,),
    )
    element_ids = [row[0] for row in await cursor.fetchall()]
    for eid in element_ids:
        if await restore_element(db, eid, restored_by=restored_by):
            count += 1

    return count


async def empty_recycle_bin(db: aiosqlite.Connection) -> int:
    """Permanently delete all soft-deleted items. Returns total count removed."""
    count = 0

    # Hard-delete all soft-deleted diagrams (with related data)
    cursor = await db.execute(
        "SELECT id FROM diagrams WHERE is_deleted = 1",
    )
    diagram_ids = [row[0] for row in await cursor.fetchall()]
    for did in diagram_ids:
        await _hard_delete_single(db, "diagram", did)
        count += 1

    # Hard-delete all soft-deleted elements (with related data)
    cursor = await db.execute(
        "SELECT id FROM elements WHERE is_deleted = 1",
    )
    element_ids = [row[0] for row in await cursor.fetchall()]
    for eid in element_ids:
        await _hard_delete_single(db, "element", eid)
        count += 1

    # Hard-delete all soft-deleted packages (with related data)
    cursor = await db.execute(
        "SELECT id FROM packages WHERE is_deleted = 1",
    )
    package_ids = [row[0] for row in await cursor.fetchall()]
    for pid in package_ids:
        await _hard_delete_single(db, "package", pid)
        count += 1

    await db.commit()
    return count


async def _hard_delete_single(
    db: aiosqlite.Connection,
    item_type: str,
    item_id: str,
) -> None:
    """Remove a single item and its related rows (no commit)."""
    if item_type == "diagram":
        await db.execute("DELETE FROM comments WHERE target_type = 'diagram' AND target_id = ?", (item_id,))
        await db.execute("DELETE FROM diagram_tags WHERE diagram_id = ?", (item_id,))
        await db.execute("DELETE FROM diagram_thumbnails WHERE diagram_id = ?", (item_id,))
        await db.execute("DELETE FROM diagrams_fts WHERE diagram_id = ?", (item_id,))
        await db.execute("DELETE FROM bookmarks WHERE diagram_id = ?", (item_id,))
        await db.execute("DELETE FROM diagram_versions WHERE diagram_id = ?", (item_id,))
        await db.execute("DELETE FROM diagrams WHERE id = ?", (item_id,))
    elif item_type == "element":
        # Delete relationships referencing this element (and their versions)
        cursor = await db.execute(
            "SELECT id FROM relationships WHERE source_element_id = ? OR target_element_id = ?",
            (item_id, item_id),
        )
        rel_ids = [row[0] for row in await cursor.fetchall()]
        for rid in rel_ids:
            await db.execute("DELETE FROM relationship_versions WHERE relationship_id = ?", (rid,))
            await db.execute("DELETE FROM relationships WHERE id = ?", (rid,))
        await db.execute("DELETE FROM comments WHERE target_type = 'element' AND target_id = ?", (item_id,))
        await db.execute("DELETE FROM element_tags WHERE element_id = ?", (item_id,))
        await db.execute("DELETE FROM elements_fts WHERE element_id = ?", (item_id,))
        await db.execute("DELETE FROM element_versions WHERE element_id = ?", (item_id,))
        await db.execute("DELETE FROM elements WHERE id = ?", (item_id,))
    elif item_type == "package":
        # Nullify parent_package_id references from child packages
        await db.execute(
            "UPDATE packages SET parent_package_id = NULL WHERE parent_package_id = ?",
            (item_id,),
        )
        # Nullify parent_package_id references from diagrams
        await db.execute(
            "UPDATE diagrams SET parent_package_id = NULL WHERE parent_package_id = ?",
            (item_id,),
        )
        # Delete package_relationships referencing this package
        await db.execute(
            "DELETE FROM package_relationships WHERE source_package_id = ? OR target_package_id = ?",
            (item_id, item_id),
        )
        await db.execute("DELETE FROM bookmarks WHERE package_id = ?", (item_id,))
        await db.execute("DELETE FROM package_versions WHERE package_id = ?", (item_id,))
        await db.execute("DELETE FROM packages WHERE id = ?", (item_id,))


async def hard_delete_item(
    db: aiosqlite.Connection,
    item_type: str,
    item_id: str,
) -> bool:
    """Permanently delete a soft-deleted item and all its version rows."""
    table_map = {"package": "packages", "diagram": "diagrams", "element": "elements"}
    table = table_map.get(item_type)
    if not table:
        return False

    # Only delete items that are already soft-deleted
    cursor = await db.execute(
        f"SELECT id FROM {table} WHERE id = ? AND is_deleted = 1",  # noqa: S608
        (item_id,),
    )
    if await cursor.fetchone() is None:
        return False

    await _hard_delete_single(db, item_type, item_id)
    await db.commit()
    return True
