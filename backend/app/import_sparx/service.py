"""Main orchestrator for SparxEA .qea file import."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.entities.service import create_entity
from app.import_sparx.converter import ea_rect_to_position
from app.import_sparx.mapper import map_connector_type, map_diagram_type, map_object_type
from app.import_sparx.reader import (
    QeaElement,
    QeaPackage,
    read_attributes,
    read_connectors,
    read_diagram_objects,
    read_diagrams,
    read_elements,
    read_packages,
)
from app.models_crud.service import create_model
from app.relationships.service import create_relationship

if TYPE_CHECKING:
    import aiosqlite


@dataclass
class ImportWarning:
    category: str
    message: str


@dataclass
class ImportSummary:
    models_created: int = 0
    entities_created: int = 0
    relationships_created: int = 0
    diagrams_created: int = 0
    elements_skipped: int = 0
    connectors_skipped: int = 0
    warnings: list[ImportWarning] = field(default_factory=list)


def _topo_sort_packages(packages: list[QeaPackage]) -> list[QeaPackage]:
    """Sort packages so parents come before children."""
    by_id = {p.Package_ID: p for p in packages}
    visited: set[int] = set()
    result: list[QeaPackage] = []

    def visit(pkg: QeaPackage) -> None:
        if pkg.Package_ID in visited:
            return
        visited.add(pkg.Package_ID)
        if pkg.Parent_ID in by_id and pkg.Parent_ID != 0:
            visit(by_id[pkg.Parent_ID])
        result.append(pkg)

    for p in packages:
        visit(p)
    return result


def _build_element_index(elements: list[QeaElement]) -> dict[int, QeaElement]:
    """Build a lookup dict from Object_ID to QeaElement."""
    return {e.Object_ID: e for e in elements}


async def import_sparx_file(
    db: aiosqlite.Connection,
    qea_path: str,
    imported_by: str,
    set_id: str | None = None,
) -> ImportSummary:
    """Import a SparxEA .qea file into Iris."""
    summary = ImportSummary()

    # 1. Read all data from .qea file
    packages = await read_packages(qea_path)
    elements = await read_elements(qea_path)
    connectors = await read_connectors(qea_path)
    diagrams = await read_diagrams(qea_path)
    diagram_objects = await read_diagram_objects(qea_path)
    attributes = await read_attributes(qea_path)

    # Build element index for fast lookups
    element_index = _build_element_index(elements)

    # 2. Build package hierarchy -> create Iris models for packages
    # Map ea_package_id -> iris_model_id
    package_model_map: dict[int, str] = {}

    for pkg in _topo_sort_packages(packages):
        parent_iris_id = package_model_map.get(pkg.Parent_ID)
        model = await create_model(
            db,
            model_type="uml",
            name=pkg.Name or f"Package {pkg.Package_ID}",
            description=None,
            data={},
            created_by=imported_by,
            parent_model_id=parent_iris_id,
            set_id=set_id,
        )
        package_model_map[pkg.Package_ID] = model["id"]  # type: ignore[assignment]
        summary.models_created += 1

    # 3. Create entities for elements
    # Map ea_object_id -> iris_entity_id
    element_entity_map: dict[int, str] = {}

    # Build attribute lookup by Object_ID
    attrs_by_object: dict[int, list[object]] = {}
    for attr in attributes:
        attrs_by_object.setdefault(attr.Object_ID, []).append(attr)

    for elem in elements:
        if elem.Object_Type is None:
            summary.elements_skipped += 1
            continue

        iris_type = map_object_type(elem.Object_Type)
        if iris_type is None:
            summary.elements_skipped += 1
            continue
        if iris_type == "_package":
            continue  # Already handled as hierarchy

        entity_data: dict[str, object] = {}
        # Add class attributes if present
        obj_attrs = attrs_by_object.get(elem.Object_ID, [])
        if obj_attrs:
            entity_data["attributes"] = [
                f"{a.Name}: {a.Type}" if a.Type else (a.Name or "")
                for a in obj_attrs  # type: ignore[union-attr]
            ]

        entity = await create_entity(
            db,
            entity_type=iris_type,
            name=elem.Name or f"Element {elem.Object_ID}",
            description=elem.Note,
            data=entity_data,
            created_by=imported_by,
            set_id=set_id,
        )
        element_entity_map[elem.Object_ID] = entity["id"]  # type: ignore[assignment]
        summary.entities_created += 1

    # 4. Create relationships for connectors
    for conn in connectors:
        if conn.Connector_Type is None:
            summary.connectors_skipped += 1
            continue

        iris_type = map_connector_type(conn.Connector_Type)
        if iris_type is None:
            summary.connectors_skipped += 1
            continue

        source_id = element_entity_map.get(conn.Start_Object_ID)
        target_id = element_entity_map.get(conn.End_Object_ID)
        if not source_id or not target_id:
            summary.connectors_skipped += 1
            continue
        if source_id == target_id:
            summary.connectors_skipped += 1
            continue

        await create_relationship(
            db,
            source_entity_id=source_id,
            target_entity_id=target_id,
            relationship_type=iris_type,
            label=conn.Name,
            description=None,
            data={},
            created_by=imported_by,
        )
        summary.relationships_created += 1

    # 5. Create diagram models with canvas data
    # Build diagram_objects lookup
    diag_objects_by_diagram: dict[int, list[object]] = {}
    for dobj in diagram_objects:
        diag_objects_by_diagram.setdefault(dobj.Diagram_ID, []).append(dobj)

    for diag in diagrams:
        model_type = map_diagram_type(diag.Diagram_Type or "")
        parent_iris_id = package_model_map.get(diag.Package_ID)

        # Build canvas nodes from diagram objects
        nodes: list[dict[str, object]] = []
        edges: list[dict[str, object]] = []
        dobjs = diag_objects_by_diagram.get(diag.Diagram_ID, [])

        for dobj in dobjs:
            entity_id = element_entity_map.get(dobj.Object_ID)  # type: ignore[union-attr]
            if not entity_id:
                continue

            pos = ea_rect_to_position(
                dobj.RectLeft,  # type: ignore[union-attr]
                dobj.RectRight,  # type: ignore[union-attr]
                dobj.RectTop,  # type: ignore[union-attr]
                dobj.RectBottom,  # type: ignore[union-attr]
            )

            # Find the element to get its type and name
            elem = element_index.get(dobj.Object_ID)  # type: ignore[union-attr]
            iris_type_str = (
                map_object_type(elem.Object_Type) if elem and elem.Object_Type else "component"
            )

            node_id = str(uuid.uuid4())
            nodes.append({
                "id": node_id,
                "type": iris_type_str or "component",
                "position": {"x": pos["x"], "y": pos["y"]},
                "data": {
                    "label": elem.Name if elem else "Unknown",
                    "entityType": iris_type_str or "component",
                    "entityId": entity_id,
                },
                "measured": {
                    "width": pos["width"],
                    "height": pos["height"],
                },
            })

        # Build edges from connectors that connect nodes on this diagram
        node_entity_to_node_id: dict[str, str] = {}
        for n in nodes:
            data = n.get("data")
            if isinstance(data, dict):
                eid = data.get("entityId")
                if eid:
                    node_entity_to_node_id[eid] = n["id"]  # type: ignore[assignment]

        for conn in connectors:
            source_eid = element_entity_map.get(conn.Start_Object_ID)
            target_eid = element_entity_map.get(conn.End_Object_ID)
            if not source_eid or not target_eid:
                continue
            source_node = node_entity_to_node_id.get(source_eid)
            target_node = node_entity_to_node_id.get(target_eid)
            if not source_node or not target_node:
                continue

            iris_conn_type = (
                map_connector_type(conn.Connector_Type) if conn.Connector_Type else "association"
            ) or "association"
            edges.append({
                "id": str(uuid.uuid4()),
                "source": source_node,
                "target": target_node,
                "type": iris_conn_type,
                "data": {
                    "relationshipType": iris_conn_type,
                    "label": conn.Name or "",
                },
            })

        model_data: dict[str, object] = {"nodes": nodes, "edges": edges}

        await create_model(
            db,
            model_type=model_type,
            name=diag.Name or f"Diagram {diag.Diagram_ID}",
            description=None,
            data=model_data,
            created_by=imported_by,
            parent_model_id=parent_iris_id,
            set_id=set_id,
        )
        summary.diagrams_created += 1

    return summary
