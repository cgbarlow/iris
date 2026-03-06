"""Main orchestrator for SparxEA .qea file import."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.diagrams.service import create_diagram
from app.elements.service import create_element
from app.import_sparx.converter import build_edge_visual, build_node_visual, ea_rect_to_position
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
    packages_skipped: int = 0
    elements_created: int = 0
    relationships_created: int = 0
    diagrams_created: int = 0
    diagrams_skipped: int = 0
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


async def _build_guid_index(
    db: "aiosqlite.Connection",
    set_id: str | None,
) -> dict[str, str]:
    """Build a GUID -> Iris ID lookup for existing items in a set.

    Scans packages, elements, and diagrams metadata for ea_guid values.
    Returns a dict mapping ea_guid to the existing Iris item ID.
    """
    guid_index: dict[str, str] = {}
    if not set_id:
        return guid_index

    # Packages: ea_guid in metadata JSON via package_versions
    cursor = await db.execute(
        "SELECT p.id, pv.metadata FROM packages p "
        "JOIN package_versions pv ON p.id = pv.package_id AND p.current_version = pv.version "
        "WHERE p.set_id = ? AND p.is_deleted = 0",
        (set_id,),
    )
    async for row in cursor:
        if row[1]:
            import json
            try:
                meta = json.loads(row[1])
                if meta.get("ea_guid"):
                    guid_index[meta["ea_guid"]] = row[0]
            except (json.JSONDecodeError, TypeError):
                pass

    # Elements: ea_guid in metadata JSON via element_versions
    cursor = await db.execute(
        "SELECT e.id, ev.metadata FROM elements e "
        "JOIN element_versions ev ON e.id = ev.element_id AND e.current_version = ev.version "
        "WHERE e.set_id = ? AND e.is_deleted = 0",
        (set_id,),
    )
    async for row in cursor:
        if row[1]:
            import json
            try:
                meta = json.loads(row[1])
                if meta.get("ea_guid"):
                    guid_index[meta["ea_guid"]] = row[0]
            except (json.JSONDecodeError, TypeError):
                pass

    # Diagrams: ea_guid in metadata JSON via diagram_versions
    cursor = await db.execute(
        "SELECT d.id, dv.metadata FROM diagrams d "
        "JOIN diagram_versions dv ON d.id = dv.diagram_id AND d.current_version = dv.version "
        "WHERE d.set_id = ? AND d.is_deleted = 0",
        (set_id,),
    )
    async for row in cursor:
        if row[1]:
            import json
            try:
                meta = json.loads(row[1])
                if meta.get("ea_guid"):
                    guid_index[meta["ea_guid"]] = row[0]
            except (json.JSONDecodeError, TypeError):
                pass

    return guid_index


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

    # Build GUID index for idempotent re-import
    guid_index = await _build_guid_index(db, set_id)

    # 2. Build package hierarchy -> create Iris packages
    # Map ea_package_id -> iris_package_id
    package_map: dict[int, str] = {}

    for pkg in _topo_sort_packages(packages):
        # Skip if package already exists (idempotent re-import)
        if pkg.ea_guid and pkg.ea_guid in guid_index:
            package_map[pkg.Package_ID] = guid_index[pkg.ea_guid]
            summary.packages_skipped += 1
            continue

        parent_iris_id = package_map.get(pkg.Parent_ID)
        # Build metadata from package-type element and tagged values
        pkg_metadata: dict[str, object] | None = None
        pkg_elem = pkg_type_elements.get(pkg.Package_ID)
        md: dict[str, object] = {}
        if pkg.ea_guid:
            md["ea_guid"] = pkg.ea_guid
        if pkg_elem:
            for field in ("Status", "Stereotype", "Version", "Scope",
                          "Author", "Complexity", "Phase", "CreatedDate",
                          "ModifiedDate", "GenType"):
                val = getattr(pkg_elem, field, None)
                if val:
                    md[field.lower()] = val
            # Include tagged values from the package-type element
            elem_tvs = tags_by_object.get(pkg_elem.Object_ID, [])
            if elem_tvs:
                md["tagged_values"] = elem_tvs
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

        # Skip if element already exists (idempotent re-import)
        if elem.ea_guid and elem.ea_guid in guid_index:
            element_map[elem.Object_ID] = guid_index[elem.ea_guid]
            summary.elements_skipped += 1
            continue

        # Build element metadata
        element_metadata: dict[str, object] | None = None
        em: dict[str, object] = {}
        if elem.ea_guid:
            em["ea_guid"] = elem.ea_guid
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
        # Skip if diagram already exists (idempotent re-import)
        if diag.ea_guid and diag.ea_guid in guid_index:
            summary.diagrams_skipped += 1
            continue

        diagram_type, diagram_notation = map_diagram_type(diag.Diagram_Type or "")
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
            # Store stereotype for theme resolution
            if elem and elem.Stereotype:
                node_data["stereotype"] = elem.Stereotype

            # Build visual overrides from EA style data
            node_visual = build_node_visual(
                dobj.ObjectStyle,  # type: ignore[union-attr]
                elem.Backcolor if elem else None,
                elem.Fontcolor if elem else None,
                elem.Bordercolor if elem else None,
                elem.BorderWidth if elem else None,
            )
            # Include explicit dimensions from EA in visual overrides
            visual_with_size: dict[str, object] = node_visual or {}
            visual_with_size["width"] = pos["width"]
            visual_with_size["height"] = pos["height"]
            node_data["visual"] = visual_with_size

            # Thread element attributes to canvas node for compartment rendering
            obj_attrs = attrs_by_object.get(dobj.Object_ID)  # type: ignore[union-attr]
            if obj_attrs:
                node_data["attributes"] = [
                    {
                        "name": a.Name or "",  # type: ignore[union-attr]
                        "type": a.Type or "",  # type: ignore[union-attr]
                        "scope": a.Scope,  # type: ignore[union-attr]
                    }
                    for a in obj_attrs
                ]

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
            route_map = {0: "bezier", 1: "step", 2: "step", 3: "step", 4: "step", 5: "step"}
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

            # Build edge visual overrides
            edge_visual = build_edge_visual(
                conn.LineColor, conn.IsBold, conn.LineStyle,
            )
            if edge_visual:
                edge_data["visual"] = edge_visual

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

        # Build diagram metadata with ea_guid
        diag_metadata: dict[str, object] | None = None
        if diag.ea_guid:
            diag_metadata = {"ea_guid": diag.ea_guid}

        await create_diagram(
            db,
            diagram_type=diagram_type,
            name=diag.Name or f"Diagram {diag.Diagram_ID}",
            description=diag.Notes,
            data=model_data,
            created_by=imported_by,
            parent_package_id=parent_iris_id,
            set_id=set_id,
            notation=diagram_notation,
            metadata=diag_metadata,
            change_summary=f"Imported from SparxEA diagram ({diag.Diagram_Type})",
        )
        summary.diagrams_created += 1

    return summary
