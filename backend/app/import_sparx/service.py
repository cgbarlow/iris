"""Main orchestrator for SparxEA .qea file import."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.diagrams.service import create_diagram
from app.elements.service import create_element
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
    read_tagged_values,
)
from app.package_relationships.service import create_package_relationship
from app.packages.service import create_package
from app.relationships.service import create_relationship

if TYPE_CHECKING:
    import aiosqlite


@dataclass
class ImportWarning:
    category: str
    message: str


@dataclass
class ImportSummary:
    packages_created: int = 0
    elements_created: int = 0
    relationships_created: int = 0
    diagrams_created: int = 0
    elements_skipped: int = 0
    connectors_skipped: int = 0
    package_relationships_created: int = 0
    warnings: list[ImportWarning] = field(default_factory=list)


def derive_note_label(html_content: str | None, fallback: str) -> str:
    """Derive a label from HTML content for Note/Boundary elements.

    Strips HTML tags, takes first non-empty line, truncates to 60 chars.
    Returns fallback if content is None or empty after stripping.
    """
    if not html_content:
        return fallback

    # Replace block-level closing tags and <br> with newlines before stripping
    text = re.sub(r"<br\s*/?>", "\n", html_content, flags=re.IGNORECASE)
    text = re.sub(r"</(?:p|div|li|h[1-6])>", "\n", text, flags=re.IGNORECASE)
    # Strip all remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode common HTML entities
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ")

    # Take first non-empty line
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped:
            if len(stripped) > 60:
                return stripped[:60] + "..."
            return stripped

    return fallback


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
    tagged_values = await read_tagged_values(qea_path)

    # Build element index for fast lookups
    element_index = _build_element_index(elements)

    # Build tagged values lookup by Object_ID
    tags_by_object: dict[int, list[dict[str, str | None]]] = {}
    for tv in tagged_values:
        tags_by_object.setdefault(tv.Object_ID, []).append(
            {"property": tv.Property, "value": tv.Value}
        )

    # Build package-type element lookup (for Status/Stereotype on packages)
    pkg_type_elements: dict[int, QeaElement] = {}
    for elem in elements:
        if elem.Object_Type == "Package":
            pkg_type_elements[elem.Package_ID] = elem

    # Build reverse map: element Object_ID -> Package_ID (for Package->Package deps)
    element_to_package: dict[int, int] = {}
    for elem in elements:
        if elem.Object_Type == "Package":
            element_to_package[elem.Object_ID] = elem.Package_ID

    # 2. Build package hierarchy -> create Iris packages
    # Map ea_package_id -> iris_package_id
    package_map: dict[int, str] = {}

    for pkg in _topo_sort_packages(packages):
        parent_iris_id = package_map.get(pkg.Parent_ID)
        # Build metadata from package-type element (Status/Stereotype)
        pkg_metadata: dict[str, object] | None = None
        pkg_elem = pkg_type_elements.get(pkg.Package_ID)
        if pkg_elem:
            md: dict[str, object] = {}
            if pkg_elem.Status:
                md["status"] = pkg_elem.Status
            if pkg_elem.Stereotype:
                md["stereotype"] = pkg_elem.Stereotype
            if md:
                pkg_metadata = md

        package = await create_package(
            db,
            name=pkg.Name or f"Package {pkg.Package_ID}",
            description=pkg.Notes,
            created_by=imported_by,
            parent_package_id=parent_iris_id,
            set_id=set_id,
            metadata=pkg_metadata,
            change_summary=f"Imported from SparxEA ({pkg.Name})",
        )
        package_map[pkg.Package_ID] = package["id"]  # type: ignore[assignment]
        summary.packages_created += 1

    # 3. Create elements for EA elements
    # Map ea_object_id -> iris_element_id
    element_map: dict[int, str] = {}

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

        element_data: dict[str, object] = {}
        # Add class attributes if present (rich object format)
        obj_attrs = attrs_by_object.get(elem.Object_ID, [])
        if obj_attrs:
            element_data["attributes"] = [
                {
                    "name": a.Name or "",  # type: ignore[union-attr]
                    "type": a.Type or "",  # type: ignore[union-attr]
                    "notes": a.Notes,  # type: ignore[union-attr]
                    "default": a.Default,  # type: ignore[union-attr]
                    "lower_bound": a.LowerBound,  # type: ignore[union-attr]
                    "upper_bound": a.UpperBound,  # type: ignore[union-attr]
                    "stereotype": a.Stereotype,  # type: ignore[union-attr]
                    "scope": a.Scope,  # type: ignore[union-attr]
                }
                for a in obj_attrs
            ]

        # Build element metadata
        element_metadata: dict[str, object] | None = None
        em: dict[str, object] = {}
        if elem.Status:
            em["status"] = elem.Status
        if elem.Stereotype:
            em["stereotype"] = elem.Stereotype
        if elem.Version:
            em["version"] = elem.Version
        if elem.Scope:
            em["scope"] = elem.Scope
        if elem.Abstract == "1":
            em["abstract"] = True
        if elem.Persistence:
            em["persistence"] = elem.Persistence
        if elem.Author:
            em["author"] = elem.Author
        if elem.Complexity and elem.Complexity != "2":
            em["complexity"] = elem.Complexity
        if elem.Phase:
            em["phase"] = elem.Phase
        if elem.CreatedDate:
            em["created_date"] = elem.CreatedDate
        if elem.ModifiedDate:
            em["modified_date"] = elem.ModifiedDate
        if elem.GenType:
            em["gen_type"] = elem.GenType
        obj_tags = tags_by_object.get(elem.Object_ID)
        if obj_tags:
            em["tagged_values"] = obj_tags
        if em:
            element_metadata = em

        # Derive meaningful name for Note/Boundary elements with NULL Name
        if iris_type in ("note", "boundary") and not elem.Name:
            element_name = derive_note_label(
                elem.Note,
                f"{'Note' if iris_type == 'note' else 'Boundary'} {elem.Object_ID}",
            )
        else:
            element_name = elem.Name or f"Element {elem.Object_ID}"

        element = await create_element(
            db,
            element_type=iris_type,
            name=element_name,
            description=elem.Note,
            data=element_data,
            created_by=imported_by,
            set_id=set_id,
            metadata=element_metadata,
            change_summary=f"Imported from SparxEA ({elem.Object_Type})",
        )
        element_map[elem.Object_ID] = element["id"]  # type: ignore[assignment]
        summary.elements_created += 1

    # 4. Create relationships for connectors
    for conn in connectors:
        if conn.Connector_Type is None:
            summary.connectors_skipped += 1
            continue

        iris_type = map_connector_type(conn.Connector_Type)
        if iris_type is None:
            summary.connectors_skipped += 1
            continue

        source_id = element_map.get(conn.Start_Object_ID)
        target_id = element_map.get(conn.End_Object_ID)
        if not source_id or not target_id:
            # Check if this is a Package->Package connector (package relationship)
            source_pkg = element_to_package.get(conn.Start_Object_ID)
            target_pkg = element_to_package.get(conn.End_Object_ID)
            if source_pkg and target_pkg:
                source_package = package_map.get(source_pkg)
                target_package = package_map.get(target_pkg)
                if source_package and target_package:
                    try:
                        await create_package_relationship(
                            db,
                            source_package_id=source_package,
                            target_package_id=target_package,
                            relationship_type=iris_type,
                            label=conn.Name,
                            description=conn.Notes,
                            created_by=imported_by,
                        )
                        summary.package_relationships_created += 1
                    except Exception:
                        # Duplicate -- relationship already exists, not a skip
                        summary.package_relationships_created += 1
                    continue
            summary.connectors_skipped += 1
            continue

        rel_data: dict[str, object] = {}
        if conn.Direction:
            rel_data["direction"] = conn.Direction
        if conn.SourceCard:
            rel_data["sourceCardinality"] = conn.SourceCard
        if conn.DestCard:
            rel_data["targetCardinality"] = conn.DestCard
        if conn.SourceRole:
            rel_data["sourceRole"] = conn.SourceRole
        if conn.DestRole:
            rel_data["targetRole"] = conn.DestRole
        if conn.Stereotype:
            rel_data["stereotype"] = conn.Stereotype

        await create_relationship(
            db,
            source_element_id=source_id,
            target_element_id=target_id,
            relationship_type=iris_type,
            label=conn.Name,
            description=conn.Notes,
            data=rel_data,
            created_by=imported_by,
        )
        summary.relationships_created += 1

    # 5. Create diagram models with canvas data
    # Build diagram_objects lookup
    diag_objects_by_diagram: dict[int, list[object]] = {}
    for dobj in diagram_objects:
        diag_objects_by_diagram.setdefault(dobj.Diagram_ID, []).append(dobj)

    for diag in diagrams:
        diagram_type = map_diagram_type(diag.Diagram_Type or "")
        parent_iris_id = package_map.get(diag.Package_ID)

        # Build canvas nodes from diagram objects
        nodes: list[dict[str, object]] = []
        edges: list[dict[str, object]] = []
        dobjs = diag_objects_by_diagram.get(diag.Diagram_ID, [])

        for dobj in dobjs:
            element_id = element_map.get(dobj.Object_ID)  # type: ignore[union-attr]
            if not element_id:
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
            # Derive label for notes/boundaries with NULL Name
            if elem and iris_type_str in ("note", "boundary") and not elem.Name:
                node_label = derive_note_label(elem.Note, "Unknown")
            else:
                node_label = (elem.Name or "Unknown") if elem else "Unknown"

            node_data: dict[str, object] = {
                "label": node_label,
                "entityType": iris_type_str or "component",
                "entityId": element_id,
            }
            # Always populate description from element's Note content
            if elem and elem.Note:
                node_data["description"] = elem.Note

            nodes.append({
                "id": node_id,
                "type": iris_type_str or "component",
                "position": {"x": pos["x"], "y": pos["y"]},
                "data": node_data,
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
            source_eid = element_map.get(conn.Start_Object_ID)
            target_eid = element_map.get(conn.End_Object_ID)
            if not source_eid or not target_eid:
                continue
            source_node = node_entity_to_node_id.get(source_eid)
            target_node = node_entity_to_node_id.get(target_eid)
            if not source_node or not target_node:
                continue

            iris_conn_type = (
                map_connector_type(conn.Connector_Type) if conn.Connector_Type else "association"
            ) or "association"

            # Build edge metadata
            route_map = {0: "bezier", 3: "step"}
            edge_data: dict[str, object] = {
                "relationshipType": iris_conn_type,
                "label": conn.Name or "",
            }
            if conn.SourceCard:
                edge_data["sourceCardinality"] = conn.SourceCard
            if conn.DestCard:
                edge_data["targetCardinality"] = conn.DestCard
            if conn.SourceRole:
                edge_data["sourceRole"] = conn.SourceRole
            if conn.DestRole:
                edge_data["targetRole"] = conn.DestRole
            if conn.Stereotype:
                edge_data["stereotype"] = conn.Stereotype
            if conn.Direction:
                edge_data["direction"] = conn.Direction
            if conn.RouteStyle is not None:
                edge_data["routingType"] = route_map.get(conn.RouteStyle, "bezier")

            # Self-loop edge
            if source_node == target_node:
                edges.append({
                    "id": str(uuid.uuid4()),
                    "source": source_node,
                    "target": target_node,
                    "type": "self_loop",
                    "sourceHandle": "right",
                    "targetHandle": "top",
                    "data": edge_data,
                })
            else:
                edges.append({
                    "id": str(uuid.uuid4()),
                    "source": source_node,
                    "target": target_node,
                    "type": iris_conn_type,
                    "data": edge_data,
                })

        model_data: dict[str, object] = {"nodes": nodes, "edges": edges}

        await create_diagram(
            db,
            diagram_type=diagram_type,
            name=diag.Name or f"Diagram {diag.Diagram_ID}",
            description=diag.Notes,
            data=model_data,
            created_by=imported_by,
            parent_package_id=parent_iris_id,
            set_id=set_id,
            change_summary=f"Imported from SparxEA diagram ({diag.Diagram_Type})",
        )
        summary.diagrams_created += 1

    return summary
