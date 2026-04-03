"""Graph data service per SPEC-116-A.

Returns all elements, diagrams, and packages as nodes, and all
relationship types as edges for a scoped set or collection.
"""

from __future__ import annotations

import json
import uuid
from collections import Counter
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


async def get_graph_data(
    db: DatabasePort,
    *,
    set_id: str | None = None,
    collection_id: str | None = None,
) -> dict[str, Any]:
    """Return nodes and edges for the multi-entity knowledge graph."""
    unscoped = not set_id and not collection_id

    # ── NODES ──────────────────────────────────────────────────────

    # 0. Collections & Sets
    if set_id:
        # Set-scoped: no need for collections
        collection_rows: list[tuple[object, ...]] = []
    elif collection_id:
        cursor = await db.execute(
            "SELECT c.id, c.name, c.description FROM collections c WHERE c.is_deleted = 0 AND c.id = ?",
            [collection_id],
        )
        collection_rows = await cursor.fetchall()
    else:
        cursor = await db.execute(
            "SELECT c.id, c.name, c.description FROM collections c WHERE c.is_deleted = 0",
        )
        collection_rows = await cursor.fetchall()
    collection_ids = {r[0] for r in collection_rows}

    if unscoped:
        cursor = await db.execute(
            "SELECT s.id, s.name, s.description, s.collection_id FROM sets s WHERE s.is_deleted = 0",
        )
    elif collection_id:
        cursor = await db.execute(
            "SELECT s.id, s.name, s.description, s.collection_id FROM sets s "
            "WHERE s.is_deleted = 0 AND s.collection_id = ?",
            [collection_id],
        )
    else:
        cursor = await db.execute(
            "SELECT s.id, s.name, s.description, s.collection_id FROM sets s "
            "WHERE s.is_deleted = 0 AND s.id = ?",
            [set_id],
        )
    set_rows = await cursor.fetchall()
    set_ids = {r[0] for r in set_rows}

    # Unscoped / collection-scoped: show collections, sets, and diagrams only
    # (skip elements/packages — too many nodes for the proxy to handle)
    if not set_id:
        diag_filter = ""
        diag_params: list[object] = []
        if collection_id:
            diag_filter = "AND d.set_id IN (SELECT id FROM sets WHERE collection_id = ?)"
            diag_params = [collection_id]
        cursor = await db.execute(
            "SELECT d.id, dv.name, d.diagram_type, dv.description, d.parent_package_id, d.set_id "
            "FROM diagrams d "
            "JOIN diagram_versions dv ON d.id = dv.diagram_id AND d.current_version = dv.version "
            f"WHERE d.is_deleted = 0 {diag_filter}",  # noqa: S608
            diag_params,
        )
        diagram_rows_unscoped = await cursor.fetchall()

        edges: list[dict[str, Any]] = []
        # Collection → Set
        for row in set_rows:
            sid, col_id = row[0], row[3]
            if col_id and col_id in collection_ids:
                edges.append({
                    "id": str(uuid.uuid4()),
                    "source": col_id, "target": sid,
                    "relationship_type": "contains",
                    "label": None,
                    "edge_type": "collection_membership",
                })
        # Set → Diagram
        for row in diagram_rows_unscoped:
            did, sid = row[0], row[5]
            if sid and sid in set_ids:
                edges.append({
                    "id": str(uuid.uuid4()),
                    "source": sid, "target": did,
                    "relationship_type": "contains",
                    "label": None,
                    "edge_type": "set_membership",
                })
        # Diagram links
        diagram_ids_unscoped = {r[0] for r in diagram_rows_unscoped}
        if diagram_ids_unscoped:
            dh = ",".join("?" * len(diagram_ids_unscoped))
            diag_list = list(diagram_ids_unscoped)
            cursor = await db.execute(
                f"SELECT id, source_diagram_id, target_diagram_id, link_type, label "  # noqa: S608
                f"FROM diagram_links "
                f"WHERE source_diagram_id IN ({dh}) AND target_diagram_id IN ({dh})",
                [*diag_list, *diag_list],
            )
            for r in await cursor.fetchall():
                edges.append({"id": r[0], "source": r[1], "target": r[2],
                               "relationship_type": r[3] or "navigation", "label": r[4],
                               "edge_type": "diagram_link"})

        rel_counts: Counter[str] = Counter()
        for e in edges:
            rel_counts[e["source"]] += 1
            rel_counts[e["target"]] += 1
        nodes: list[dict[str, Any]] = []
        for r in collection_rows:
            nodes.append({"id": r[0], "name": r[1], "node_type": "collection",
                           "type_detail": "collection", "relationship_count": rel_counts.get(r[0], 0)})
        for r in set_rows:
            nodes.append({"id": r[0], "name": r[1], "node_type": "set",
                           "type_detail": "set", "relationship_count": rel_counts.get(r[0], 0)})
        for r in diagram_rows_unscoped:
            nodes.append({"id": r[0], "name": r[1], "node_type": "diagram",
                           "type_detail": r[2], "relationship_count": rel_counts.get(r[0], 0)})
        return {"nodes": nodes, "edges": edges}

    # Build scope filter for entities
    if set_id:
        entity_filter = "AND {a}.set_id = ?"
        entity_params: list[object] = [set_id]
    else:
        entity_filter = "AND {a}.set_id IN (SELECT id FROM sets WHERE collection_id = ?)"
        entity_params = [collection_id]

    # 1. Elements
    cursor = await db.execute(
        "SELECT e.id, ev.name, e.element_type, ev.description, e.set_id "
        "FROM elements e "
        "JOIN element_versions ev ON e.id = ev.element_id AND e.current_version = ev.version "
        f"WHERE e.is_deleted = 0 {entity_filter.format(a='e')}",  # noqa: S608
        entity_params,
    )
    element_rows = await cursor.fetchall()
    element_ids = {r[0] for r in element_rows}

    # 2. Diagrams
    cursor = await db.execute(
        "SELECT d.id, dv.name, d.diagram_type, dv.description, d.parent_package_id, dv.data, d.set_id "
        "FROM diagrams d "
        "JOIN diagram_versions dv ON d.id = dv.diagram_id AND d.current_version = dv.version "
        f"WHERE d.is_deleted = 0 {entity_filter.format(a='d')}",  # noqa: S608
        entity_params,
    )
    diagram_rows = await cursor.fetchall()
    diagram_ids = {r[0] for r in diagram_rows}

    # 3. Packages
    cursor = await db.execute(
        "SELECT p.id, pv.name, pv.description, p.parent_package_id, p.set_id "
        "FROM packages p "
        "JOIN package_versions pv ON p.id = pv.package_id AND p.current_version = pv.version "
        f"WHERE p.is_deleted = 0 {entity_filter.format(a='p')}",  # noqa: S608
        entity_params,
    )
    package_rows = await cursor.fetchall()
    package_ids = {r[0] for r in package_rows}

    # ── EDGES ──────────────────────────────────────────────────────

    edges: list[dict[str, Any]] = []

    # 1. Element-to-element relationships
    cursor = await db.execute(
        "SELECT r.id, r.source_element_id, r.target_element_id, "
        "r.relationship_type, rv.label "
        "FROM relationships r "
        "JOIN relationship_versions rv ON r.id = rv.relationship_id AND r.current_version = rv.version "
        "JOIN elements se ON r.source_element_id = se.id AND se.is_deleted = 0 "
        "JOIN elements te ON r.target_element_id = te.id AND te.is_deleted = 0 "
        f"WHERE r.is_deleted = 0 {entity_filter.format(a='se')} "  # noqa: S608
        f"{entity_filter.format(a='te')}",  # noqa: S608
        [*entity_params, *entity_params],
    )
    for r in await cursor.fetchall():
        edges.append({"id": r[0], "source": r[1], "target": r[2],
                       "relationship_type": r[3], "label": r[4],
                       "edge_type": "element_relationship"})

    # 2. Package-to-package relationships
    if package_ids:
        ph = ",".join("?" * len(package_ids))
        pkg_list = list(package_ids)
        cursor = await db.execute(
            f"SELECT id, source_package_id, target_package_id, relationship_type, label "  # noqa: S608
            f"FROM package_relationships "
            f"WHERE source_package_id IN ({ph}) AND target_package_id IN ({ph})",
            [*pkg_list, *pkg_list],
        )
        for r in await cursor.fetchall():
            edges.append({"id": r[0], "source": r[1], "target": r[2],
                           "relationship_type": r[3], "label": r[4],
                           "edge_type": "package_relationship"})

    # 3. Diagram-to-diagram links
    if diagram_ids:
        dh = ",".join("?" * len(diagram_ids))
        diag_list = list(diagram_ids)
        cursor = await db.execute(
            f"SELECT id, source_diagram_id, target_diagram_id, link_type, label "  # noqa: S608
            f"FROM diagram_links "
            f"WHERE source_diagram_id IN ({dh}) AND target_diagram_id IN ({dh})",
            [*diag_list, *diag_list],
        )
        for r in await cursor.fetchall():
            edges.append({"id": r[0], "source": r[1], "target": r[2],
                           "relationship_type": r[3] or "navigation", "label": r[4],
                           "edge_type": "diagram_link"})

    # 4 & 5. Diagram→element and diagram→package (from canvas data)
    for row in diagram_rows:
        diagram_id = row[0]
        data_str = row[5]
        if not data_str:
            continue
        try:
            data = json.loads(data_str) if isinstance(data_str, str) else data_str
        except (json.JSONDecodeError, TypeError):
            continue
        nodes_list = data.get("nodes") if isinstance(data, dict) else None
        if not isinstance(nodes_list, list):
            continue
        for canvas_node in nodes_list:
            if not isinstance(canvas_node, dict):
                continue
            node_data = canvas_node.get("data")
            if not isinstance(node_data, dict):
                continue
            # Diagram → Element
            entity_id = node_data.get("entityId")
            if entity_id and entity_id in element_ids:
                edges.append({
                    "id": str(uuid.uuid4()),
                    "source": diagram_id, "target": entity_id,
                    "relationship_type": "contains",
                    "label": None,
                    "edge_type": "diagram_element",
                })
            # Diagram → Package
            linked_pkg = node_data.get("linkedPackageId")
            if linked_pkg and linked_pkg in package_ids:
                edges.append({
                    "id": str(uuid.uuid4()),
                    "source": diagram_id, "target": linked_pkg,
                    "relationship_type": "references",
                    "label": None,
                    "edge_type": "diagram_package",
                })

    # 6. Hierarchy edges (parent_package_id)
    for row in diagram_rows:
        diagram_id, parent_pkg = row[0], row[4]
        if parent_pkg and parent_pkg in package_ids:
            edges.append({
                "id": str(uuid.uuid4()),
                "source": parent_pkg, "target": diagram_id,
                "relationship_type": "contains",
                "label": None,
                "edge_type": "hierarchy",
            })
    for row in package_rows:
        pkg_id, parent_pkg = row[0], row[3]
        if parent_pkg and parent_pkg in package_ids:
            edges.append({
                "id": str(uuid.uuid4()),
                "source": parent_pkg, "target": pkg_id,
                "relationship_type": "contains",
                "label": None,
                "edge_type": "hierarchy",
            })

    # 7. Collection → Set membership
    for row in set_rows:
        sid, col_id = row[0], row[3]
        if col_id and col_id in collection_ids:
            edges.append({
                "id": str(uuid.uuid4()),
                "source": col_id, "target": sid,
                "relationship_type": "contains",
                "label": None,
                "edge_type": "collection_membership",
            })

    # 8. Set → Element/Diagram/Package membership
    for row in element_rows:
        eid, sid = row[0], row[4]
        if sid and sid in set_ids:
            edges.append({
                "id": str(uuid.uuid4()),
                "source": sid, "target": eid,
                "relationship_type": "contains",
                "label": None,
                "edge_type": "set_membership",
            })
    for row in diagram_rows:
        did, sid = row[0], row[6]
        if sid and sid in set_ids:
            edges.append({
                "id": str(uuid.uuid4()),
                "source": sid, "target": did,
                "relationship_type": "contains",
                "label": None,
                "edge_type": "set_membership",
            })
    for row in package_rows:
        pid, sid = row[0], row[4]
        if sid and sid in set_ids:
            edges.append({
                "id": str(uuid.uuid4()),
                "source": sid, "target": pid,
                "relationship_type": "contains",
                "label": None,
                "edge_type": "set_membership",
            })

    # ── COUNT RELATIONSHIPS PER NODE ───────────────────────────────

    rel_counts: Counter[str] = Counter()
    for e in edges:
        rel_counts[e["source"]] += 1
        rel_counts[e["target"]] += 1

    # ── BUILD RESPONSE ─────────────────────────────────────────────

    nodes: list[dict[str, Any]] = []
    for r in collection_rows:
        nodes.append({"id": r[0], "name": r[1], "node_type": "collection",
                       "type_detail": "collection", "description": r[2],
                       "relationship_count": rel_counts.get(r[0], 0)})
    for r in set_rows:
        nodes.append({"id": r[0], "name": r[1], "node_type": "set",
                       "type_detail": "set", "description": r[2],
                       "relationship_count": rel_counts.get(r[0], 0)})
    for r in element_rows:
        nodes.append({"id": r[0], "name": r[1], "node_type": "element",
                       "type_detail": r[2], "description": r[3],
                       "relationship_count": rel_counts.get(r[0], 0)})
    for r in diagram_rows:
        nodes.append({"id": r[0], "name": r[1], "node_type": "diagram",
                       "type_detail": r[2], "description": r[3],
                       "relationship_count": rel_counts.get(r[0], 0)})
    for r in package_rows:
        nodes.append({"id": r[0], "name": r[1], "node_type": "package",
                       "type_detail": "package", "description": r[2],
                       "relationship_count": rel_counts.get(r[0], 0)})

    return {"nodes": nodes, "edges": edges}
