"""Main orchestrator for SparxEA .qea file import."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.diagrams.service import create_diagram
from app.elements.service import create_element
from app.import_sparx.converter import build_edge_visual, build_node_visual, ea_rect_to_position, format_uml_visibility, parse_diagram_link_geometry, parse_diagram_link_path, parse_nid
from app.import_sparx.icon_matcher import SemanticIconMatcher
from app.import_sparx.mapper import map_archimate_stereotype, map_connector_type, map_diagram_type, map_object_type
from app.import_sparx.reader import (
    QeaElement,
    QeaPackage,
    read_attributes,
    read_connectors,
    read_diagram_links,
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
    diagrams_updated: int = 0
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


def strip_label_from_note(label: str, note_text: str) -> str:
    """Strip the label prefix from note text to avoid duplicate title display.

    If note_text starts with label followed by a line break, returns the
    remainder only. Otherwise returns note_text unchanged.
    """
    for sep in ("\r\n", "\n"):
        prefix = label + sep
        if note_text.startswith(prefix):
            return note_text[len(prefix):].lstrip("\r\n")
    return note_text


def compute_auto_handles(
    src_x: int, src_y: int, src_w: int, src_h: int,
    tgt_x: int, tgt_y: int, tgt_w: int, tgt_h: int,
) -> tuple[str, str]:
    """Compute optimal source/target handle sides from node geometry.

    Compares node center positions and returns the handle side pair
    (sourceHandle, targetHandle) that produces the shortest connection.
    """
    src_cx = src_x + src_w / 2
    src_cy = src_y + src_h / 2
    tgt_cx = tgt_x + tgt_w / 2
    tgt_cy = tgt_y + tgt_h / 2

    dx = tgt_cx - src_cx
    dy = tgt_cy - src_cy

    if abs(dx) >= abs(dy):
        # Predominantly horizontal
        if dx >= 0:
            return ("right", "left")
        return ("left", "right")
    # Predominantly vertical
    if dy >= 0:
        return ("bottom", "top")
    return ("top", "bottom")


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
    diagram_links = await read_diagram_links(qea_path)
    attributes = await read_attributes(qea_path)
    tagged_values = await read_tagged_values(qea_path)

    # Build element index for fast lookups
    element_index = _build_element_index(elements)

    # Initialize semantic icon matcher for NavigationCell icons (ADR-091-B)
    icon_matcher = SemanticIconMatcher()

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

        iris_type = map_object_type(elem.Object_Type, elem.Stereotype)
        if iris_type is None:
            summary.elements_skipped += 1
            continue
        # Abstract classes get a distinct type so UML renderer applies italic styling
        if iris_type == "class" and elem.Abstract == "1":
            iris_type = "abstract_class"

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
        elif iris_type == "navigation_cell" and not elem.Name:
            # NavigationCell: use Alias, then target diagram name, as element name
            nav_target_id = None
            if elem.PDATA1:
                try:
                    nav_target_id = int(elem.PDATA1)
                except (ValueError, TypeError):
                    pass
            ea_diag_name_lookup = {d.Diagram_ID: (d.Name or "") for d in diagrams}
            fallback = elem.Alias or f"Navigation {elem.Object_ID}"
            element_name = ea_diag_name_lookup.get(nav_target_id, fallback) if nav_target_id else fallback
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

        # EA stores composition/aggregation as Association with SourceIsAggregate/DestIsAggregate flags
        # 0=none, 1=shared (aggregation), 2=composite (composition)
        if iris_type == "association":
            if conn.SourceIsAggregate == 2 or conn.DestIsAggregate == 2:
                iris_type = "composition"
            elif conn.SourceIsAggregate == 1 or conn.DestIsAggregate == 1:
                iris_type = "aggregation"

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
            prefix = format_uml_visibility(conn.SourceAccess)
            rel_data["sourceRole"] = f"{prefix}{conn.SourceRole}"
        if conn.DestRole:
            prefix = format_uml_visibility(conn.DestAccess)
            rel_data["targetRole"] = f"{prefix}{conn.DestRole}"
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
    # Build package name lookup for cross-package qualifiers
    package_names: dict[int, str] = {p.Package_ID: (p.Name or "") for p in packages}

    # Build EA diagram name lookup for NavigationCell label resolution
    ea_diagram_names: dict[int, str] = {d.Diagram_ID: (d.Name or "") for d in diagrams}

    # Build diagram_objects lookup
    diag_objects_by_diagram: dict[int, list[object]] = {}
    for dobj in diagram_objects:
        diag_objects_by_diagram.setdefault(dobj.Diagram_ID, []).append(dobj)

    # Build diagram_links lookup: (DiagramID, ConnectorID) -> QeaDiagramLink
    diag_links_index: dict[tuple[int, int], object] = {}
    for dlink in diagram_links:
        diag_links_index[(dlink.DiagramID, dlink.ConnectorID)] = dlink

    ea_diagram_id_to_iris: dict[int, str] = {}

    for diag in diagrams:
        # Check if diagram already exists for update-on-reimport
        existing_iris_id: str | None = None
        if diag.ea_guid and diag.ea_guid in guid_index:
            existing_iris_id = guid_index[diag.ea_guid]
            ea_diagram_id_to_iris[diag.Diagram_ID] = existing_iris_id

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
                map_object_type(elem.Object_Type, elem.Stereotype) if elem and elem.Object_Type else "component"
            )
            # Abstract classes get a distinct type for italic rendering in UML
            if iris_type_str == "class" and elem and elem.Abstract == "1":
                iris_type_str = "abstract_class"
            # ArchiMate stereotype override: EA stores ArchiMate elements as
            # standard UML types (Class, Component, Activity) with ArchiMate
            # stereotypes — use the stereotype to select the correct Iris type.
            if elem and elem.Stereotype:
                archimate_type = map_archimate_stereotype(elem.Stereotype)
                if archimate_type:
                    iris_type_str = archimate_type

            node_id = str(uuid.uuid4())
            # Derive label for notes/boundaries with NULL Name
            if elem and iris_type_str in ("note", "boundary") and not elem.Name:
                node_label = derive_note_label(elem.Note, "Unknown")
            elif elem and iris_type_str == "navigation_cell":
                # NavigationCell: PDATA1 is the EA Diagram_ID the cell links to.
                # Use the target diagram's name as the card label, falling back to
                # Alias (used by Prolaborate for tiles without a target diagram).
                target_diag_id = None
                if elem.PDATA1:
                    try:
                        target_diag_id = int(elem.PDATA1)
                    except (ValueError, TypeError):
                        pass
                if target_diag_id:
                    node_label = ea_diagram_names.get(target_diag_id, elem.Alias or elem.Name or "Unknown")
                else:
                    node_label = elem.Alias or elem.Name or "Unknown"
            else:
                node_label = (elem.Name or "Unknown") if elem else "Unknown"

            node_data: dict[str, object] = {
                "label": node_label,
                "entityType": iris_type_str or "component",
                "entityId": element_id,
            }
            # NavigationCell: store target EA diagram ID for post-processing
            # (will be resolved to Iris UUID after all diagrams are created)
            if elem and iris_type_str == "navigation_cell":
                if elem.PDATA1:
                    try:
                        node_data["_targetEaDiagramId"] = int(elem.PDATA1)
                    except (ValueError, TypeError):
                        pass
                # Extract Prolaborate icon NID from StyleEx (e.g. "NID=2-13;")
                nid = parse_nid(elem.StyleEx)
                if nid:
                    node_data["navIconId"] = nid
                # Semantic icon matching: use the element's own Name (carries semantic
                # meaning like "Stakeholder", "Organization") rather than node_label
                # which is the target diagram's name for NavigationCells.
                # Don't pass "NavigationCell" as stereotype — it's structural, not semantic,
                # and its tokens ("navigation", "cell") corrupt matching scores.
                icon_match_name = elem.Name or elem.Alias or node_label
                icon_stereotype = elem.Stereotype if elem.Stereotype != "NavigationCell" else None
                icon_ref = icon_matcher.match(
                    icon_match_name,
                    stereotype=icon_stereotype,
                    note=elem.Note,
                )
                node_data["_pendingIcon"] = icon_ref
            # Always populate description from element's Note content
            if elem and elem.Note:
                node_data["description"] = strip_label_from_note(node_label, elem.Note)
            # Store stereotype for theme resolution
            if elem and elem.Stereotype:
                node_data["stereotype"] = elem.Stereotype
            # Cross-package qualifier: show source package name when element
            # belongs to a different package than the diagram
            if elem and elem.Package_ID != diag.Package_ID:
                pkg_name = package_names.get(elem.Package_ID)
                if pkg_name:
                    node_data["qualifier"] = pkg_name

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
            # Boundaries are transparent containers — strip bgColor so CSS
            # default (transparent) applies. EA BackColor on boundaries is
            # typically not rendered as a fill in the EA UI.
            if iris_type_str == "boundary":
                visual_with_size.pop("bgColor", None)
            # Merge pending icon into visual overrides (ADR-091-B)
            pending_icon = node_data.pop("_pendingIcon", None)
            if pending_icon:
                visual_with_size["icon"] = {"set": pending_icon["set"], "name": pending_icon["name"]}
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

            node_dict: dict[str, object] = {
                "id": node_id,
                "type": iris_type_str or "component",
                "position": {"x": pos["x"], "y": pos["y"]},
                "data": node_data,
                "measured": {
                    "width": pos["width"],
                    "height": pos["height"],
                },
            }
            # Boundaries and diagram frames render behind content nodes
            if iris_type_str in ("boundary", "diagram_frame"):
                node_dict["zIndex"] = -1
            nodes.append(node_dict)

        # Build edges from connectors that connect nodes on this diagram
        node_entity_to_node_id: dict[str, str] = {}
        node_geometry: dict[str, dict[str, int]] = {}
        for n in nodes:
            data = n.get("data")
            if isinstance(data, dict):
                eid = data.get("entityId")
                if eid:
                    node_entity_to_node_id[eid] = n["id"]  # type: ignore[assignment]
            measured = n.get("measured", {})
            pos = n.get("position", {})
            node_geometry[n["id"]] = {  # type: ignore[index]
                "x": pos.get("x", 0), "y": pos.get("y", 0),  # type: ignore[union-attr]
                "w": measured.get("width", 100), "h": measured.get("height", 60),  # type: ignore[union-attr]
            }

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

            # Detect composition/aggregation from EA aggregate flags
            if iris_conn_type == "association":
                if conn.SourceIsAggregate == 2 or conn.DestIsAggregate == 2:
                    iris_conn_type = "composition"
                elif conn.SourceIsAggregate == 1 or conn.DestIsAggregate == 1:
                    iris_conn_type = "aggregation"

            # Build edge metadata
            # EA RouteStyle: 0=Direct, 1=Auto Route, 2=Custom, 3=Tree, 4=Orthogonal, 5=Orthogonal Rounded
            route_map = {0: "straight", 1: "step", 2: "straight", 3: "straight", 4: "step", 5: "smoothstep"}
            edge_data: dict[str, object] = {
                "relationshipType": iris_conn_type,
                "label": conn.Name or "",
            }
            if conn.SourceCard:
                edge_data["sourceCardinality"] = conn.SourceCard
            if conn.DestCard:
                edge_data["targetCardinality"] = conn.DestCard
            if conn.SourceRole:
                prefix = format_uml_visibility(conn.SourceAccess)
                edge_data["sourceRole"] = f"{prefix}{conn.SourceRole}"
            if conn.DestRole:
                prefix = format_uml_visibility(conn.DestAccess)
                edge_data["targetRole"] = f"{prefix}{conn.DestRole}"
            if conn.Stereotype:
                edge_data["stereotype"] = conn.Stereotype
                # Show stereotype as label when edge has no name (ADR-090)
                if not conn.Name:
                    edge_data["label"] = f"\u00AB{conn.Stereotype}\u00BB"
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

            # EA edge geometry: waypoints and connection point offsets
            dlink = diag_links_index.get((diag.Diagram_ID, conn.Connector_ID))
            if dlink:
                geom = parse_diagram_link_geometry(dlink.Geometry)  # type: ignore[union-attr]
                if geom.get("sx") or geom.get("sy"):
                    edge_data["sourceOffset"] = {"x": geom.get("sx", 0), "y": geom.get("sy", 0)}
                if geom.get("ex") or geom.get("ey"):
                    edge_data["targetOffset"] = {"x": geom.get("ex", 0), "y": geom.get("ey", 0)}
                waypoints = parse_diagram_link_path(dlink.Path)  # type: ignore[union-attr]
                if waypoints:
                    edge_data["waypoints"] = waypoints
                # EA label positions from geometry
                if geom.get("labels"):
                    edge_data["labelPositions"] = geom["labels"]

            # EA connector absolute connection points
            if conn.PtStartX and conn.PtStartY:
                edge_data["sourcePoint"] = {"x": conn.PtStartX, "y": -conn.PtStartY}
            if conn.PtEndX and conn.PtEndY:
                edge_data["targetPoint"] = {"x": conn.PtEndX, "y": -conn.PtEndY}

            # EA Start_Edge/End_Edge: map to handle side hints
            edge_handle_map = {1: "top", 2: "right", 3: "bottom", 4: "left"}
            source_handle = None
            target_handle = None
            if conn.Start_Edge and conn.Start_Edge in edge_handle_map:
                source_handle = edge_handle_map[conn.Start_Edge]
            if conn.End_Edge and conn.End_Edge in edge_handle_map:
                target_handle = edge_handle_map[conn.End_Edge]

            # Note links use center-to-center handles
            if iris_conn_type == "note_link":
                source_handle = "center"
                target_handle = "center"

            # Auto-compute handles from node geometry when EA says "auto-route"
            if not source_handle and not target_handle and source_node != target_node:
                sg = node_geometry.get(source_node, {})
                tg = node_geometry.get(target_node, {})
                if sg and tg:
                    source_handle, target_handle = compute_auto_handles(
                        sg["x"], sg["y"], sg["w"], sg["h"],
                        tg["x"], tg["y"], tg["w"], tg["h"],
                    )

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
                edge_entry: dict[str, object] = {
                    "id": str(uuid.uuid4()),
                    "source": source_node,
                    "target": target_node,
                    "type": iris_conn_type,
                    "data": edge_data,
                }
                if source_handle:
                    edge_entry["sourceHandle"] = source_handle
                if target_handle:
                    edge_entry["targetHandle"] = target_handle
                edges.append(edge_entry)

        # Add diagram frame as a canvas node so it zooms/pans with the canvas
        if diag.cx and diag.cy:
            # Compute bounding box origin from all nodes, with padding
            min_x = min((n["position"]["x"] for n in nodes), default=0) - 10  # type: ignore[index]
            min_y = min((n["position"]["y"] for n in nodes), default=0) - 40  # type: ignore[index]
            frame_node: dict[str, object] = {
                "id": str(uuid.uuid4()),
                "type": "diagram_frame",
                "position": {"x": min_x, "y": min_y},
                "data": {
                    "label": diag.Name or "",
                    "entityType": "diagram_frame",
                    "frameType": diagram_type,
                    "frameName": diag.Name or "",
                    "frameWidth": diag.cx,
                    "frameHeight": diag.cy,
                },
                "selectable": False,
                "draggable": False,
                "connectable": False,
                "zIndex": -1,
            }
            # Insert at beginning so it renders behind other nodes
            nodes.insert(0, frame_node)

        model_data: dict[str, object] = {"nodes": nodes, "edges": edges}

        # Build diagram metadata with ea_guid and theme
        diag_metadata: dict[str, object] = {"theme_id": "ea-default-uml"}
        if diag.ea_guid:
            diag_metadata["ea_guid"] = diag.ea_guid

        if existing_iris_id:
            # Update existing diagram with rebuilt canvas data
            cursor = await db.execute(
                "SELECT current_version FROM diagrams WHERE id = ?",
                (existing_iris_id,),
            )
            ver_row = await cursor.fetchone()
            if ver_row:
                current_version = ver_row[0]
                new_version = current_version + 1
                now = datetime.now(tz=UTC).isoformat()
                data_json = json.dumps(model_data)
                metadata_json = json.dumps(diag_metadata)
                await db.execute(
                    "INSERT INTO diagram_versions "
                    "(diagram_id, version, name, description, data, metadata, "
                    "change_summary, created_at, created_by) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        existing_iris_id,
                        new_version,
                        diag.Name or f"Diagram {diag.Diagram_ID}",
                        diag.Notes,
                        data_json,
                        metadata_json,
                        f"Re-imported from SparxEA diagram ({diag.Diagram_Type})",
                        now,
                        imported_by,
                    ),
                )
                await db.execute(
                    "UPDATE diagrams SET current_version = ?, updated_at = ? WHERE id = ?",
                    (new_version, now, existing_iris_id),
                )
                await db.commit()
            summary.diagrams_updated += 1
        else:
            result = await create_diagram(
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
            ea_diagram_id_to_iris[diag.Diagram_ID] = result["id"]
            summary.diagrams_created += 1

    # 6. Post-process: link NavigationCell nodes to their target diagrams.
    # NavigationCells use PDATA1 (EA Diagram_ID) to reference the diagram they
    # navigate to. Now that all diagrams have Iris UUIDs, patch linkedModelId
    # and create diagram_links records for the relationships tab.
    if ea_diagram_id_to_iris:
        for ea_diag_id, iris_diag_id in ea_diagram_id_to_iris.items():
            cursor = await db.execute(
                "SELECT version, data FROM diagram_versions WHERE diagram_id = ? ORDER BY version DESC LIMIT 1",
                (iris_diag_id,),
            )
            row = await cursor.fetchone()
            if not row:
                continue
            latest_version = row[0]
            canvas = json.loads(row[1])
            patched = False
            for node in canvas.get("nodes", []):
                nd = node.get("data", {})
                if nd.get("entityType") == "navigation_cell" and nd.get("_targetEaDiagramId"):
                    target_iris_id = ea_diagram_id_to_iris.get(nd["_targetEaDiagramId"])
                    if target_iris_id:
                        nd["linkedModelId"] = target_iris_id
                        # Create a diagram_links record so this shows in the relationships tab
                        link_id = str(uuid.uuid4())
                        await db.execute(
                            "INSERT OR IGNORE INTO diagram_links "
                            "(id, source_diagram_id, target_diagram_id, link_type, label, created_by) "
                            "VALUES (?, ?, ?, 'navigation', ?, ?)",
                            (link_id, iris_diag_id, target_iris_id, nd.get("label"), imported_by),
                        )
                    del nd["_targetEaDiagramId"]
                    patched = True
            if patched:
                await db.execute(
                    "UPDATE diagram_versions SET data = ? WHERE diagram_id = ? AND version = ?",
                    (json.dumps(canvas), iris_diag_id, latest_version),
                )
        await db.commit()

    return summary
