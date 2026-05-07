"""Orchestrator for ArchiMate Open Exchange XML (OEX) import.

Reads an OEX file, materialises elements and relationships, and either
ports the embedded views to iris diagrams or — if the file is model-only —
auto-generates a single Overview diagram with a type-grouped grid layout
so the user has something to look at after import.

Mirrors the structural shape of ``import_sparx/service.py`` but is much
smaller: OEX is a clean schema and we delegate type lookup to the existing
``ARCHIMATE_STEREOTYPE_MAP`` in import_sparx/mapper.py.
"""

from __future__ import annotations

import math
import os
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.diagrams.service import create_diagram
from app.elements.service import create_element
from app.import_archimate.mapper import (
    map_oex_element_type,
    map_oex_relationship_type,
)
from app.import_archimate.reader import OexModel, OexNode, OexView, parse_oex
from app.import_common import ImportWarning
from app.packages.service import create_package
from app.relationships.service import create_relationship

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


@dataclass
class ArchimateImportSummary:
    packages_created: int = 0
    elements_created: int = 0
    elements_skipped: int = 0
    relationships_created: int = 0
    relationships_skipped: int = 0
    diagrams_created: int = 0
    warnings: list[ImportWarning] = field(default_factory=list)


# Auto-layout: cell size accommodates the standard ArchiMate node footprint
# (120×60) plus padding for label rendering and edge clearance.
_GRID_CELL_W = 220
_GRID_CELL_H = 140


async def import_oex_file(
    db: "DatabasePort",
    path: str,
    *,
    imported_by: str,
    set_id: str | None = None,
) -> ArchimateImportSummary:
    """Import an OEX file, returning a summary of what was created."""
    summary = ArchimateImportSummary()
    model = parse_oex(path)

    pkg_name = model.name or os.path.splitext(os.path.basename(path))[0]
    package = await create_package(
        db,
        name=pkg_name,
        description=model.documentation,
        created_by=imported_by,
        set_id=set_id,
    )
    summary.packages_created += 1
    package_id = str(package["id"])

    # ---- elements ----
    element_id_by_oex: dict[str, str] = {}
    element_type_by_iris: dict[str, str] = {}
    element_name_by_iris: dict[str, str] = {}
    for oe in model.elements:
        iris_type = map_oex_element_type(oe.xsi_type)
        if not iris_type:
            summary.elements_skipped += 1
            summary.warnings.append(
                ImportWarning(
                    category="unmapped_element_type",
                    message=f"{oe.identifier}: unknown xsi:type '{oe.xsi_type}'",
                )
            )
            continue
        elem = await create_element(
            db,
            element_type=iris_type,
            name=oe.name or oe.identifier,
            description=oe.documentation,
            data={},
            created_by=imported_by,
            set_id=set_id,
            notation="archimate",
        )
        elem_id = str(elem["id"])
        element_id_by_oex[oe.identifier] = elem_id
        element_type_by_iris[elem_id] = iris_type
        element_name_by_iris[elem_id] = oe.name or oe.identifier
        summary.elements_created += 1

    # ---- relationships ----
    rel_id_by_oex: dict[str, str] = {}
    for orel in model.relationships:
        iris_type = map_oex_relationship_type(orel.xsi_type)
        src = element_id_by_oex.get(orel.source)
        tgt = element_id_by_oex.get(orel.target)
        if not iris_type or not src or not tgt:
            summary.relationships_skipped += 1
            summary.warnings.append(
                ImportWarning(
                    category="unmapped_relationship"
                    if not iris_type
                    else "dangling_relationship",
                    message=f"{orel.identifier}: skipped ({orel.xsi_type})",
                )
            )
            continue
        rel = await create_relationship(
            db,
            source_element_id=src,
            target_element_id=tgt,
            relationship_type=iris_type,
            label=orel.name,
            description=None,
            data={},
            created_by=imported_by,
        )
        rel_id_by_oex[orel.identifier] = str(rel["id"])
        summary.relationships_created += 1

    # ---- views (or auto-generated overview) ----
    if model.views:
        for view in model.views:
            await _create_diagram_from_view(
                db,
                view=view,
                model=model,
                package_id=package_id,
                element_id_by_oex=element_id_by_oex,
                element_type_by_iris=element_type_by_iris,
                element_name_by_iris=element_name_by_iris,
                imported_by=imported_by,
                set_id=set_id,
                summary=summary,
            )
    elif element_id_by_oex:
        await _create_auto_overview(
            db,
            model_name=model.name,
            package_id=package_id,
            element_id_by_oex=element_id_by_oex,
            element_type_by_iris=element_type_by_iris,
            element_name_by_iris=element_name_by_iris,
            imported_by=imported_by,
            set_id=set_id,
            summary=summary,
        )
        summary.warnings.append(
            ImportWarning(
                category="auto_layout",
                message="No views in source file — auto-generated Overview diagram.",
            )
        )

    return summary


async def _create_diagram_from_view(
    db: "DatabasePort",
    *,
    view: OexView,
    model: OexModel,
    package_id: str,
    element_id_by_oex: dict[str, str],
    element_type_by_iris: dict[str, str],
    element_name_by_iris: dict[str, str],
    imported_by: str,
    set_id: str | None,
    summary: ArchimateImportSummary,
) -> None:
    """Build canvas data from an OEX view and persist as an iris diagram."""
    nodes: list[dict[str, object]] = []
    edges: list[dict[str, object]] = []
    canvas_node_id_by_oex: dict[str, str] = {}

    def emit_node(oex: OexNode, dx: int, dy: int) -> None:
        if not oex.element_ref:
            return
        elem_id = element_id_by_oex.get(oex.element_ref)
        if not elem_id:
            return
        iris_type = element_type_by_iris.get(elem_id, "component")
        canvas_id = str(uuid.uuid4())
        canvas_node_id_by_oex[oex.identifier] = canvas_id
        nodes.append(
            {
                "id": canvas_id,
                "type": iris_type,
                "position": {"x": oex.x + dx, "y": oex.y + dy},
                "data": {
                    "label": element_name_by_iris.get(elem_id, ""),
                    "entityType": iris_type,
                    "entityId": elem_id,
                    "visual": {"width": oex.w, "height": oex.h},
                },
                "measured": {"width": oex.w, "height": oex.h},
            }
        )
        # Flatten any nested <node> children to absolute coords.
        for child in oex.children:
            emit_node(child, dx + oex.x, dy + oex.y)

    for n in view.nodes:
        emit_node(n, 0, 0)

    for c in view.connections:
        src = canvas_node_id_by_oex.get(c.source)
        tgt = canvas_node_id_by_oex.get(c.target)
        if not src or not tgt:
            continue
        edges.append(
            {
                "id": c.identifier or str(uuid.uuid4()),
                "source": src,
                "target": tgt,
                "type": "default",
                "data": {},
            }
        )

    await create_diagram(
        db,
        diagram_type="free_form",
        name=view.name or "View",
        description=None,
        data={"nodes": nodes, "edges": edges},
        created_by=imported_by,
        parent_package_id=package_id,
        set_id=set_id,
        notation="archimate",
    )
    summary.diagrams_created += 1


async def _create_auto_overview(
    db: "DatabasePort",
    *,
    model_name: str,
    package_id: str,
    element_id_by_oex: dict[str, str],
    element_type_by_iris: dict[str, str],
    element_name_by_iris: dict[str, str],
    imported_by: str,
    set_id: str | None,
    summary: ArchimateImportSummary,
) -> None:
    """Synthesise an Overview diagram with a type-grouped grid layout."""
    # Sort by iris type so nodes of the same kind cluster together.
    sorted_elem_ids = sorted(
        element_id_by_oex.values(),
        key=lambda eid: (element_type_by_iris.get(eid, ""), element_name_by_iris.get(eid, "")),
    )
    n = len(sorted_elem_ids)
    cols = max(1, int(math.ceil(math.sqrt(n))))

    nodes: list[dict[str, object]] = []
    canvas_node_by_elem: dict[str, str] = {}
    for idx, elem_id in enumerate(sorted_elem_ids):
        row, col = divmod(idx, cols)
        iris_type = element_type_by_iris.get(elem_id, "component")
        canvas_id = str(uuid.uuid4())
        canvas_node_by_elem[elem_id] = canvas_id
        nodes.append(
            {
                "id": canvas_id,
                "type": iris_type,
                "position": {
                    "x": col * _GRID_CELL_W,
                    "y": row * _GRID_CELL_H,
                },
                "data": {
                    "label": element_name_by_iris.get(elem_id, ""),
                    "entityType": iris_type,
                    "entityId": elem_id,
                    "visual": {"width": 120, "height": 60},
                },
                "measured": {"width": 120, "height": 60},
            }
        )

    # Build edges from the iris relationship graph rather than from OEX —
    # this way we don't need to thread relationship handles through and we
    # benefit from already-de-duplicated relationship data.
    edges = await _edges_from_relationships(db, canvas_node_by_elem)

    await create_diagram(
        db,
        diagram_type="free_form",
        name=f"{model_name or 'Imported'} — Overview",
        description="Auto-generated overview of the imported ArchiMate model.",
        data={"nodes": nodes, "edges": edges},
        created_by=imported_by,
        parent_package_id=package_id,
        set_id=set_id,
        notation="archimate",
    )
    summary.diagrams_created += 1


async def _edges_from_relationships(
    db: "DatabasePort",
    canvas_node_by_elem: dict[str, str],
) -> list[dict[str, object]]:
    """Pull all relationships among the given element ids and turn them into
    canvas edges. Done in one query rather than per-element to keep the cost
    O(R) for R relationships."""
    if not canvas_node_by_elem:
        return []
    elem_ids = list(canvas_node_by_elem.keys())
    placeholders = ",".join(["?"] * len(elem_ids))
    sql = (
        f"SELECT id, source_element_id, target_element_id, relationship_type "
        f"FROM relationships WHERE is_deleted = 0 "
        f"AND source_element_id IN ({placeholders}) "
        f"AND target_element_id IN ({placeholders})"
    )
    cursor = await db.execute(sql, (*elem_ids, *elem_ids))
    rows = await cursor.fetchall()

    edges: list[dict[str, object]] = []
    for row in rows:
        rel_id = row[0]
        src_node = canvas_node_by_elem.get(row[1])
        tgt_node = canvas_node_by_elem.get(row[2])
        if not src_node or not tgt_node:
            continue
        edges.append(
            {
                "id": str(rel_id),
                "source": src_node,
                "target": tgt_node,
                "type": "default",
                "data": {"relationshipType": row[3]},
            }
        )
    return edges


__all__ = ["ArchimateImportSummary", "import_oex_file"]
