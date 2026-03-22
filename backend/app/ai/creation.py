"""AI diagram creation service (ADR-094-B).

Composes layered system prompts and materialises AI-generated diagram JSON
into Iris canvas diagrams in the database.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

logger = logging.getLogger(__name__)


async def build_creation_system_prompt(
    db: aiosqlite.Connection,
    notation: str,
    diagram_type: str | None = None,
) -> str:
    """Compose a system prompt from the layered ai_creation_prompts table.

    Layer priority:
    - override (notation-specific, active): returned alone — replaces all layers.
    - base: shared instructions for all AI diagram creation.
    - notation-specific: methodology for the given notation.
    - diagram_type-specific: layout rules for the specific diagram type.

    Returns empty string if no active prompts exist.
    """
    # Check for active override for this notation
    cursor = await db.execute(
        "SELECT prompt_text FROM ai_creation_prompts "
        "WHERE layer = 'override' AND notation = ? AND is_active = 1 "
        "ORDER BY display_order LIMIT 1",
        (notation,),
    )
    override_row = await cursor.fetchone()
    if override_row:
        return override_row[0]

    parts: list[str] = []

    # Base layer
    cursor = await db.execute(
        "SELECT prompt_text FROM ai_creation_prompts "
        "WHERE layer = 'base' AND is_active = 1 "
        "ORDER BY display_order",
    )
    for row in await cursor.fetchall():
        parts.append(row[0])

    # Notation layer
    cursor = await db.execute(
        "SELECT prompt_text FROM ai_creation_prompts "
        "WHERE layer = 'notation' AND notation = ? AND is_active = 1 "
        "ORDER BY display_order",
        (notation,),
    )
    for row in await cursor.fetchall():
        parts.append(row[0])

    # Diagram type layer
    if diagram_type:
        cursor = await db.execute(
            "SELECT prompt_text FROM ai_creation_prompts "
            "WHERE layer = 'diagram_type' AND diagram_type = ? AND is_active = 1 "
            "ORDER BY display_order",
            (diagram_type,),
        )
        for row in await cursor.fetchall():
            parts.append(row[0])

    result = "\n\n".join(parts)
    logger.info("[AI_CREATION] Built system prompt: %d layers, %d chars", len(parts), len(result))
    return result


async def create_diagrams_from_ai(
    db: aiosqlite.Connection,
    set_id: str,
    ai_json: dict,
    user_id: str,
    *,
    package_id: str | None = None,
) -> list[str]:
    """Create diagrams from AI-generated JSON structure.

    Args:
        db: Database connection.
        set_id: Target set ID.
        ai_json: AI output dict with "diagrams" key.
        user_id: ID of the creating user.

    Returns:
        List of created diagram IDs in the same order as input.

    Raises:
        KeyError: If "diagrams" key is missing.
        ValueError: If ai_json structure is invalid.
    """
    diagrams_def = ai_json["diagrams"]  # raises KeyError if missing

    if not isinstance(diagrams_def, list):
        raise ValueError("'diagrams' must be a list")

    if not diagrams_def:
        return []

    now = datetime.now(tz=UTC).isoformat()
    diagram_ids: list[str] = []
    canvas_data_list: list[dict] = []

    # Phase 1: create all diagrams (linkedDiagramIndex not yet resolved)
    for diag_def in diagrams_def:
        diagram_id = str(uuid.uuid4())
        diagram_ids.append(diagram_id)

        name = diag_def.get("name", "Untitled")
        diagram_type = diag_def.get("diagram_type", "outcomes_map")
        notation = diag_def.get("notation", "doview")

        canvas_nodes = _build_canvas_nodes(diag_def.get("nodes", []))
        canvas_edges = _build_canvas_edges(diag_def.get("edges", []))
        canvas_data = {"nodes": canvas_nodes, "edges": canvas_edges}
        canvas_data_list.append(canvas_data)

        await db.execute(
            "INSERT INTO diagrams "
            "(id, set_id, diagram_type, notation, parent_package_id, "
            "current_version, created_at, created_by, updated_at, is_deleted) "
            "VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, 0)",
            (diagram_id, set_id, diagram_type, notation, package_id, now, user_id, now),
        )
        await db.execute(
            "INSERT INTO diagram_versions "
            "(diagram_id, version, name, data, change_type, created_at, created_by) "
            "VALUES (?, 1, ?, ?, 'create', ?, ?)",
            (diagram_id, name, json.dumps(canvas_data), now, user_id),
        )

    await db.commit()

    # Phase 2: resolve linkedDiagramIndex → linkedModelId in overview_tile nodes
    for i, (diagram_id, canvas_data) in enumerate(zip(diagram_ids, canvas_data_list)):
        updated = False
        for node in canvas_data.get("nodes", []):
            node_data = node.get("data", {})
            if node_data.get("entityType") == "overview_tile":
                idx = node_data.pop("_linkedDiagramIndex", None)
                if idx is not None and 0 <= idx < len(diagram_ids):
                    node_data["linkedModelId"] = diagram_ids[idx]
                    updated = True

        if updated:
            await db.execute(
                "UPDATE diagram_versions SET data = ? WHERE diagram_id = ? AND version = 1",
                (json.dumps(canvas_data), diagram_id),
            )

    await db.commit()
    return diagram_ids


def _build_canvas_nodes(ai_nodes: list[dict]) -> list[dict]:
    """Convert AI node format to Iris canvas node format."""
    canvas_nodes = []
    for ai_node in ai_nodes:
        node_id = ai_node.get("id", str(uuid.uuid4()))
        entity_type = ai_node.get("type", "outcome_box")
        label = ai_node.get("label", "")
        position = ai_node.get("position", {"x": 0, "y": 0})
        size = ai_node.get("size", {"width": 200, "height": 86})
        visual = ai_node.get("visual", {})

        node_data: dict = {
            "label": label,
            "entityType": entity_type,
        }
        if visual:
            node_data["visual"] = visual

        # Stash linkedDiagramIndex for phase-2 resolution
        linked_idx = ai_node.get("linkedDiagramIndex")
        if linked_idx is not None:
            node_data["_linkedDiagramIndex"] = linked_idx

        canvas_nodes.append({
            "id": node_id,
            "type": entity_type,
            "position": position,
            "data": node_data,
            "width": size.get("width", 200),
            "height": size.get("height", 86),
        })
    return canvas_nodes


def _build_canvas_edges(ai_edges: list[dict]) -> list[dict]:
    """Convert AI edge format to Iris canvas edge format."""
    canvas_edges = []
    for ai_edge in ai_edges:
        edge_id = ai_edge.get("id", str(uuid.uuid4()))
        edge_type = ai_edge.get("type", "causal_link")
        source = ai_edge.get("source", "")
        target = ai_edge.get("target", "")
        visual = ai_edge.get("visual", {})

        edge_data: dict = {
            "relationshipType": edge_type,
        }
        if visual:
            edge_data["visual"] = visual

        canvas_edges.append({
            "id": edge_id,
            "type": edge_type,
            "source": source,
            "target": target,
            "sourceHandle": "center",
            "targetHandle": "center",
            "data": edge_data,
        })
    return canvas_edges
