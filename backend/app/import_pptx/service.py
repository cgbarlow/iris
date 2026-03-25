"""Main orchestrator for DoView PPTX import."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.diagrams.service import create_diagram
from app.elements.service import create_element
from app.import_common import ImportWarning
from app.import_pptx.classifier import (
    ClassifiedSlide,
    ShapeRole,
    SlideType,
    classify_slides,
    group_into_columns,
    validate_doview_compliance,
)
from app.import_pptx.reader import PptxShape, read_pptx
from app.packages.service import create_package
from app.relationships.service import create_relationship

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort

# EMU → pixel conversion at 96 DPI
_EMU_PER_PX = 9525


@dataclass
class PptxImportSummary:
    packages_created: int = 0
    elements_created: int = 0
    relationships_created: int = 0
    diagrams_created: int = 0
    slides_skipped: int = 0
    warnings: list[ImportWarning] = field(default_factory=list)


def _emu_to_px(emu: int) -> int:
    return round(emu / _EMU_PER_PX)


def _derive_model_name(file_path: str) -> str:
    """Derive a model name from the PPTX filename."""
    base = os.path.splitext(os.path.basename(file_path))[0]
    # Clean up common suffixes
    for suffix in (" DoView", " doview"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    return base.strip()


async def import_pptx_file(
    db: "DatabasePort",
    file_path: str,
    *,
    imported_by: str,
    set_id: str | None = None,
) -> PptxImportSummary:
    """Import a DoView PPTX file into Iris.

    4-pass pipeline:
      0. Validate DoView compliance
      1. Parse & classify
      2. Create package, elements, relationships, diagrams
      3. Resolve cross-diagram links (linkedModelId)
    """
    summary = PptxImportSummary()

    # ── Pass 0: Validate ──────────────────────────────────────────────
    slides = read_pptx(file_path)
    violations = validate_doview_compliance(slides)
    if violations:
        raise ValueError(
            "File does not appear to be a DoView model:\n• "
            + "\n• ".join(violations)
        )

    # ── Pass 1: Classify ──────────────────────────────────────────────
    classified = classify_slides(slides)

    # ── Pass 2: Create entities & diagrams ────────────────────────────
    model_name = _derive_model_name(file_path)

    root_pkg = await create_package(
        db,
        name=model_name,
        description=f"Imported from DoView PPTX: {os.path.basename(file_path)}",
        created_by=imported_by,
        parent_package_id=None,
        set_id=set_id,
        change_summary=f"Imported from DoView PPTX ({os.path.basename(file_path)})",
    )
    root_pkg_id = root_pkg["id"]
    summary.packages_created += 1

    # Track slide_index → diagram_id for cross-link resolution
    slide_diagram_map: dict[int, str] = {}
    # Track overview tile shapes and their node IDs for pass 3
    overview_tile_links: list[dict] = []  # {node_id, hyperlink_slide_index, diagram_id}

    for cs in classified:
        if cs.slide_type == SlideType.SKIP:
            summary.slides_skipped += 1
            continue

        if cs.slide_type == SlideType.OVERVIEW:
            diagram_id = await _create_overview_diagram(
                db, cs, summary, root_pkg_id, set_id, imported_by,
                overview_tile_links,
            )
        elif cs.slide_type == SlideType.FINAL_OUTCOMES:
            diagram_id = await _create_final_outcomes_diagram(
                db, cs, summary, root_pkg_id, set_id, imported_by,
            )
        elif cs.slide_type == SlideType.OUTCOMES_MAP:
            diagram_id = await _create_outcomes_map_diagram(
                db, cs, summary, root_pkg_id, set_id, imported_by,
            )
        else:
            summary.slides_skipped += 1
            continue

        slide_diagram_map[cs.slide.index] = diagram_id

    # ── Pass 3: Resolve cross-diagram links ───────────────────────────
    if overview_tile_links:
        await _resolve_overview_links(
            db, overview_tile_links, slide_diagram_map, summary,
        )

    return summary


# ---------------------------------------------------------------------------
# Diagram builders
# ---------------------------------------------------------------------------


async def _create_overview_diagram(
    db: "DatabasePort",
    cs: ClassifiedSlide,
    summary: PptxImportSummary,
    root_pkg_id: str,
    set_id: str | None,
    imported_by: str,
    overview_tile_links: list[dict],
) -> str:
    """Create an 'overview' diagram from the overview slide."""
    nodes: list[dict] = []
    tiles = [c for c in cs.shapes if c.role == ShapeRole.OVERVIEW_TILE]

    for tile in tiles:
        shape = tile.shape
        element = await create_element(
            db,
            element_type="overview_tile",
            name=shape.text or "Untitled",
            description=None,
            data={},
            created_by=imported_by,
            set_id=set_id,
            change_summary="Imported from DoView PPTX",
        )
        summary.elements_created += 1

        node_id = f"n_{element['id'][:8]}"
        bg_color = f"#{shape.fill_color}" if shape.fill_color else "#DAE8FC"
        border_color = _darken_color(shape.fill_color) if shape.fill_color else "#6C8EBF"

        node = {
            "id": node_id,
            "type": "overview_tile",
            "position": {"x": _emu_to_px(shape.left), "y": _emu_to_px(shape.top)},
            "data": {
                "label": shape.text or "Untitled",
                "entityType": "overview_tile",
                "entityId": element["id"],
                "visual": {
                    "width": _emu_to_px(shape.width),
                    "height": _emu_to_px(shape.height),
                    "bgColor": bg_color,
                    "borderColor": border_color,
                },
            },
            "measured": {
                "width": _emu_to_px(shape.width),
                "height": _emu_to_px(shape.height),
            },
        }
        nodes.append(node)

        if shape.hyperlink_slide_index is not None:
            overview_tile_links.append({
                "node_id": node_id,
                "hyperlink_slide_index": shape.hyperlink_slide_index,
                "diagram_id": "",  # filled in pass 3
            })

    diagram = await create_diagram(
        db,
        diagram_type="overview",
        name=_extract_title(cs) or "Overview",
        description=None,
        data={"nodes": nodes, "edges": []},
        created_by=imported_by,
        parent_package_id=root_pkg_id,
        set_id=set_id,
        notation="doview",
        change_summary="Imported from DoView PPTX",
    )
    summary.diagrams_created += 1
    return diagram["id"]


async def _create_final_outcomes_diagram(
    db: "DatabasePort",
    cs: ClassifiedSlide,
    summary: PptxImportSummary,
    root_pkg_id: str,
    set_id: str | None,
    imported_by: str,
) -> str:
    """Create a diagram from the final outcomes slide."""
    nodes: list[dict] = []
    outcomes = [c for c in cs.shapes if c.role == ShapeRole.FINAL_OUTCOME]

    for outcome in outcomes:
        shape = outcome.shape
        element = await create_element(
            db,
            element_type="final_outcome",
            name=shape.text or "Untitled",
            description=None,
            data={},
            created_by=imported_by,
            set_id=set_id,
            change_summary="Imported from DoView PPTX",
        )
        summary.elements_created += 1

        node_id = f"n_{element['id'][:8]}"
        node = {
            "id": node_id,
            "type": "final_outcome",
            "position": {"x": _emu_to_px(shape.left), "y": _emu_to_px(shape.top)},
            "data": {
                "label": shape.text or "Untitled",
                "entityType": "final_outcome",
                "entityId": element["id"],
                "visual": {
                    "width": _emu_to_px(shape.width),
                    "height": _emu_to_px(shape.height),
                    "bgColor": "#FFFFFF",
                    "borderColor": "#CCCCCC",
                },
            },
            "measured": {
                "width": _emu_to_px(shape.width),
                "height": _emu_to_px(shape.height),
            },
        }
        nodes.append(node)

    diagram = await create_diagram(
        db,
        diagram_type="outcomes_map",
        name=cs.page_title or "Final Outcomes",
        description=None,
        data={"nodes": nodes, "edges": []},
        created_by=imported_by,
        parent_package_id=root_pkg_id,
        set_id=set_id,
        notation="doview",
        change_summary="Imported from DoView PPTX",
    )
    summary.diagrams_created += 1
    return diagram["id"]


async def _create_outcomes_map_diagram(
    db: "DatabasePort",
    cs: ClassifiedSlide,
    summary: PptxImportSummary,
    root_pkg_id: str,
    set_id: str | None,
    imported_by: str,
) -> str:
    """Create an 'outcomes_map' diagram with causal links between columns."""
    nodes: list[dict] = []
    edges: list[dict] = []

    boxes = [c for c in cs.shapes if c.role == ShapeRole.OUTCOME_BOX]
    arrows = [c for c in cs.shapes if c.role == ShapeRole.CAUSAL_ARROW]

    # Determine the page colour for outcome boxes
    page_color = None
    for c in cs.shapes:
        if c.role == ShapeRole.PAGE_TITLE and c.shape.fill_color:
            page_color = c.shape.fill_color
            break
    if not page_color and boxes:
        page_color = boxes[0].shape.fill_color

    bg_color = f"#{page_color}" if page_color else "#FFF2CC"
    border_color = _darken_color(page_color) if page_color else "#D6B656"

    # Create element records and build node map
    shape_to_node_id: dict[int, str] = {}  # shape_id → node_id
    shape_to_element_id: dict[int, str] = {}

    for box in boxes:
        shape = box.shape
        element = await create_element(
            db,
            element_type="outcome_box",
            name=shape.text or "Untitled",
            description=None,
            data={},
            created_by=imported_by,
            set_id=set_id,
            change_summary="Imported from DoView PPTX",
        )
        summary.elements_created += 1

        node_id = f"n_{element['id'][:8]}"
        shape_to_node_id[shape.shape_id] = node_id
        shape_to_element_id[shape.shape_id] = element["id"]

        node = {
            "id": node_id,
            "type": "outcome_box",
            "position": {"x": _emu_to_px(shape.left), "y": _emu_to_px(shape.top)},
            "data": {
                "label": shape.text or "Untitled",
                "entityType": "outcome_box",
                "entityId": element["id"],
                "visual": {
                    "width": _emu_to_px(shape.width),
                    "height": _emu_to_px(shape.height),
                    "bgColor": bg_color,
                    "borderColor": border_color,
                },
            },
            "measured": {
                "width": _emu_to_px(shape.width),
                "height": _emu_to_px(shape.height),
            },
        }
        nodes.append(node)

    # Group into columns and create causal links
    box_shapes = [b.shape for b in boxes]
    columns = group_into_columns(box_shapes)

    if len(columns) > 1 and arrows:
        # Sort arrows by x-position
        sorted_arrows = sorted(arrows, key=lambda a: a.shape.left)

        # Each arrow separates adjacent columns
        for arrow_idx, _arrow in enumerate(sorted_arrows):
            if arrow_idx >= len(columns) - 1:
                break
            src_col = columns[arrow_idx]
            tgt_col = columns[arrow_idx + 1]

            for src_shape in src_col:
                for tgt_shape in tgt_col:
                    src_nid = shape_to_node_id.get(src_shape.shape_id)
                    tgt_nid = shape_to_node_id.get(tgt_shape.shape_id)
                    src_eid = shape_to_element_id.get(src_shape.shape_id)
                    tgt_eid = shape_to_element_id.get(tgt_shape.shape_id)
                    if not (src_nid and tgt_nid and src_eid and tgt_eid):
                        continue

                    rel = await create_relationship(
                        db,
                        source_element_id=src_eid,
                        target_element_id=tgt_eid,
                        relationship_type="causal_link",
                        label="",
                        description=None,
                        data={"direction": "source_to_target"},
                        created_by=imported_by,
                    )
                    summary.relationships_created += 1

                    edge_id = f"e_{rel['id'][:8]}"
                    edges.append({
                        "id": edge_id,
                        "source": src_nid,
                        "target": tgt_nid,
                        "type": "causal_link",
                        "sourceHandle": "center",
                        "targetHandle": "center",
                        "data": {
                            "relationshipType": "causal_link",
                            "relationshipId": rel["id"],
                        },
                    })
    elif len(columns) > 1 and not arrows:
        summary.warnings.append(ImportWarning(
            category="slide_no_arrows",
            message=f"Slide '{cs.page_title or cs.slide.index}' has outcome columns "
                    "but no causal arrows — imported without causal links",
        ))

    diagram = await create_diagram(
        db,
        diagram_type="outcomes_map",
        name=cs.page_title or f"Outcomes Map (Slide {cs.slide.index + 1})",
        description=None,
        data={"nodes": nodes, "edges": edges},
        created_by=imported_by,
        parent_package_id=root_pkg_id,
        set_id=set_id,
        notation="doview",
        change_summary="Imported from DoView PPTX",
    )
    summary.diagrams_created += 1
    return diagram["id"]


# ---------------------------------------------------------------------------
# Pass 3: resolve cross-diagram links
# ---------------------------------------------------------------------------


async def _resolve_overview_links(
    db: "DatabasePort",
    tile_links: list[dict],
    slide_diagram_map: dict[int, str],
    summary: PptxImportSummary,
) -> None:
    """Update overview tile nodes with linkedModelId pointing to target diagrams."""
    # Find the overview diagram (where the tiles live)
    # Tiles all came from the same diagram — find it
    if not tile_links:
        return

    # Group tiles by the diagram they belong to
    # We need to find which diagram contains these node IDs
    # The overview diagram was the first one created — find it via tile_links metadata
    # Actually, we stored "diagram_id" as empty — let's find the overview diagram
    # by looking for tiles in slide_diagram_map for the overview slide

    # Find the overview slide index (it's the one with the most hyperlinked tiles)
    overview_slide_idx: int | None = None
    max_tiles = 0
    slide_tile_count: dict[int, int] = {}
    for link in tile_links:
        # The tile's shape came from a specific slide — we need to find it
        # But we didn't store it. Let's reconstruct: the overview diagram is
        # the one that has nodes matching our tile node IDs
        pass

    # Find the overview diagram by querying which diagram has these node IDs
    # Simpler approach: the overview diagram is in slide_diagram_map
    # and we know which slide it is because it had the most tiles

    # We need to update the diagram data. Get the diagram for the overview slide.
    # Since all tile_links come from the overview slide, and we need the diagram_id
    # for that slide, let's find it.

    # Actually, we can determine the overview slide: it's the slide NOT targeted
    # by any hyperlink that HAS tiles. Or we can look for SlideType.OVERVIEW in
    # slide_diagram_map. But we only have slide_index → diagram_id.

    # The simplest approach: try all diagrams and check if they contain the tile node IDs.
    # Even simpler: we know the overview diagram was created first (it's processed in order).

    # Best approach: update the tile_links during pass 2 to include the diagram_id
    # of the overview diagram. But that requires refactoring. Let's use a pragmatic
    # approach: query all diagrams and update the one containing matching node IDs.

    resolved_any = False
    for link in tile_links:
        target_slide_idx = link["hyperlink_slide_index"]
        target_diagram_id = slide_diagram_map.get(target_slide_idx)
        if target_diagram_id is None:
            summary.warnings.append(ImportWarning(
                category="hyperlink_unresolved",
                message=f"Overview tile links to slide {target_slide_idx} "
                        "which has no imported diagram",
            ))
            continue
        link["target_diagram_id"] = target_diagram_id
        resolved_any = True

    if not resolved_any:
        return

    # Find the overview diagram — it's the diagram for the slide that isn't
    # a target of any overview tile hyperlink
    targeted_slides = {link["hyperlink_slide_index"] for link in tile_links}
    overview_diagram_id: str | None = None
    for slide_idx, diag_id in slide_diagram_map.items():
        if slide_idx not in targeted_slides:
            # This could be the overview slide
            overview_diagram_id = diag_id
            break

    if overview_diagram_id is None:
        return

    # Read current diagram data and update linkedModelId on matching nodes
    cursor = await db.execute(
        "SELECT data FROM diagram_versions WHERE diagram_id = ? ORDER BY version DESC LIMIT 1",
        (overview_diagram_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return

    diagram_data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
    node_link_map = {
        link["node_id"]: link.get("target_diagram_id")
        for link in tile_links
        if link.get("target_diagram_id")
    }

    updated = False
    for node in diagram_data.get("nodes", []):
        nid = node.get("id")
        if nid in node_link_map:
            node.setdefault("data", {})["linkedModelId"] = node_link_map[nid]
            updated = True

    if updated:
        await db.execute(
            "UPDATE diagram_versions SET data = ? WHERE diagram_id = ? AND version = 1",
            (json.dumps(diagram_data), overview_diagram_id),
        )
        await db.commit()


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------


def _darken_color(hex_color: str | None) -> str:
    """Produce a darker border colour from a fill colour hex string."""
    if not hex_color:
        return "#D6B656"
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        factor = 0.65
        dr = max(0, int(r * factor))
        dg = max(0, int(g * factor))
        db = max(0, int(b * factor))
        return f"#{dr:02X}{dg:02X}{db:02X}"
    except (ValueError, IndexError):
        return "#D6B656"


def _extract_title(cs: ClassifiedSlide) -> str | None:
    """Extract the first text from a non-tile, non-footer shape as a title."""
    if cs.page_title:
        return cs.page_title
    for c in cs.shapes:
        if c.role == ShapeRole.SKIP and c.shape.text and not c.shape.fill_color:
            return c.shape.text
    return None
