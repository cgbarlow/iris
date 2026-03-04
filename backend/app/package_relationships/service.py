"""Package relationship CRUD service."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def create_package_relationship(
    db: aiosqlite.Connection,
    *,
    source_package_id: str,
    target_package_id: str,
    relationship_type: str,
    label: str | None = None,
    description: str | None = None,
    created_by: str,
) -> dict[str, object]:
    """Create a package-to-package relationship."""
    rel_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()

    await db.execute(
        "INSERT INTO package_relationships "
        "(id, source_package_id, target_package_id, relationship_type, label, description, "
        "created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (rel_id, source_package_id, target_package_id, relationship_type,
         label, description, created_by, now),
    )
    await db.commit()

    return {
        "id": rel_id,
        "source_package_id": source_package_id,
        "target_package_id": target_package_id,
        "relationship_type": relationship_type,
        "label": label,
        "description": description,
        "created_by": created_by,
        "created_at": now,
    }


async def list_package_relationships(
    db: aiosqlite.Connection,
    package_id: str,
) -> list[dict[str, object]]:
    """List all relationships where package_id is source or target."""
    cursor = await db.execute(
        "SELECT pr.id, pr.source_package_id, pr.target_package_id, "
        "pr.relationship_type, pr.label, pr.description, "
        "pr.created_by, pr.created_at, "
        "spv.name AS source_name, tpv.name AS target_name "
        "FROM package_relationships pr "
        "JOIN packages sp ON pr.source_package_id = sp.id "
        "JOIN package_versions spv ON sp.id = spv.package_id AND sp.current_version = spv.version "
        "JOIN packages tp ON pr.target_package_id = tp.id "
        "JOIN package_versions tpv ON tp.id = tpv.package_id AND tp.current_version = tpv.version "
        "WHERE pr.source_package_id = ? OR pr.target_package_id = ? "
        "ORDER BY pr.created_at DESC",
        (package_id, package_id),
    )
    rows = await cursor.fetchall()
    return [
        {
            "id": r[0],
            "source_package_id": r[1],
            "target_package_id": r[2],
            "relationship_type": r[3],
            "label": r[4],
            "description": r[5],
            "created_by": r[6],
            "created_at": r[7],
            "source_name": r[8],
            "target_name": r[9],
        }
        for r in rows
    ]


async def list_element_relationships_for_diagram(
    db: aiosqlite.Connection,
    diagram_id: str,
) -> list[dict[str, object]]:
    """List element-to-element relationships for elements on a diagram's canvas."""
    # Get diagram's canvas data to extract element IDs
    cursor = await db.execute(
        "SELECT dv.data FROM diagrams d "
        "JOIN diagram_versions dv ON d.id = dv.diagram_id AND d.current_version = dv.version "
        "WHERE d.id = ? AND d.is_deleted = 0",
        (diagram_id,),
    )
    row = await cursor.fetchone()
    if not row or not row[0]:
        return []

    try:
        data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
    except (json.JSONDecodeError, TypeError):
        return []

    nodes = data.get("nodes", [])
    element_ids: set[str] = set()
    for node in nodes:
        node_data = node.get("data", {})
        if isinstance(node_data, dict):
            eid = node_data.get("elementId")
            if eid:
                element_ids.add(eid)

    if not element_ids:
        return []

    # Query relationships where both source and target are in this diagram's elements
    placeholders = ",".join("?" for _ in element_ids)
    id_list = list(element_ids)
    cursor = await db.execute(
        f"SELECT r.id, r.source_element_id, r.target_element_id, "  # noqa: S608
        f"r.relationship_type, rv.label, rv.description, "
        f"r.created_by, r.created_at, "
        f"sev.name AS source_name, tev.name AS target_name "
        f"FROM relationships r "
        f"JOIN relationship_versions rv ON r.id = rv.relationship_id "
        f"  AND r.current_version = rv.version "
        f"LEFT JOIN elements se ON r.source_element_id = se.id "
        f"LEFT JOIN element_versions sev ON se.id = sev.element_id "
        f"  AND se.current_version = sev.version "
        f"LEFT JOIN elements te ON r.target_element_id = te.id "
        f"LEFT JOIN element_versions tev ON te.id = tev.element_id "
        f"  AND te.current_version = tev.version "
        f"WHERE r.is_deleted = 0 "
        f"  AND (r.source_element_id IN ({placeholders}) "
        f"       OR r.target_element_id IN ({placeholders})) "
        f"ORDER BY r.created_at DESC",
        id_list + id_list,
    )
    rows = await cursor.fetchall()
    return [
        {
            "id": r[0],
            "source_element_id": r[1],
            "target_element_id": r[2],
            "relationship_type": r[3],
            "label": r[4],
            "description": r[5],
            "created_by": r[6],
            "created_at": r[7],
            "source_name": r[8] or "",
            "target_name": r[9] or "",
        }
        for r in rows
    ]


async def list_all_relationships_for_diagram(
    db: aiosqlite.Connection,
    diagram_id: str,
) -> dict[str, list[dict[str, object]]]:
    """Return both package-to-package and element-to-element relationships for a diagram."""
    # For package relationships, we need to find which package this diagram belongs to
    # and then list package relationships for that package
    cursor = await db.execute(
        "SELECT parent_package_id FROM diagrams WHERE id = ? AND is_deleted = 0",
        (diagram_id,),
    )
    row = await cursor.fetchone()
    package_rels: list[dict[str, object]] = []
    if row and row[0]:
        package_rels = await list_package_relationships(db, row[0])

    element_rels = await list_element_relationships_for_diagram(db, diagram_id)
    return {
        "package_relationships": package_rels,
        "element_relationships": element_rels,
    }


async def delete_package_relationship(
    db: aiosqlite.Connection,
    relationship_id: str,
) -> bool:
    """Delete a package relationship. Returns False if not found."""
    cursor = await db.execute(
        "DELETE FROM package_relationships WHERE id = ?",
        (relationship_id,),
    )
    await db.commit()
    return cursor.rowcount > 0
