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

from app.elements.materialise import materialise_element, materialise_relationship

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

    # Preamble: when both notation and diagram_type are present, make the
    # user's UI selection explicit so the AI does not re-ask for information
    # it already has (ADR-132). Also remind the AI to use attached context.
    if diagram_type:
        preamble = (
            f"## User selection (already confirmed in UI)\n\n"
            f"- Notation: **{notation}**\n"
            f"- Diagram type: **{diagram_type}**\n\n"
            "Do NOT ask the user to re-confirm the notation or the diagram "
            "type — they are already fixed.\n\n"
            "If the Set context or attached documents below describe the "
            "subject matter, treat them as the primary source and do not "
            "ask the user to describe what is already in them. Proceed to "
            "propose structure (Stage 1) based on that material, then "
            "confirm with the user.\n"
        )
        result = f"{preamble}\n{result}"

    print(f"[AI_CREATION] Built system prompt: {len(parts)} layers, {len(result)} chars", flush=True)
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

        print(f"[AI_APPLY] Creating diagram '{name}' type={diagram_type} package_id={package_id}", flush=True)
        await db.execute(
            "INSERT INTO diagrams "
            "(id, set_id, diagram_type, notation, parent_package_id, "
            "current_version, created_at, created_by, updated_at, is_deleted) "
            "VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, FALSE)",
            (diagram_id, set_id, diagram_type, notation, package_id, now, user_id, now),
        )
        await db.execute(
            "INSERT INTO diagram_versions "
            "(diagram_id, version, name, data, change_type, created_at, created_by) "
            "VALUES (?, 1, ?, ?, 'create', ?, ?)",
            (diagram_id, name, json.dumps(canvas_data), now, user_id),
        )

    await db.commit()

    # Phase 1.5: materialise elements and relationships for each diagram
    for i, (diagram_id, canvas_data, diag_def) in enumerate(
        zip(diagram_ids, canvas_data_list, diagrams_def)
    ):
        notation = diag_def.get("notation", "doview")
        node_element_map: dict[str, str] = {}  # node_id → element_id

        # Create element for each node
        for node in canvas_data.get("nodes", []):
            node_data = node.get("data", {})
            element_id = str(uuid.uuid4())
            node_id = node.get("id", "")
            node_element_map[node_id] = element_id

            await materialise_element(
                db,
                element_id=element_id,
                element_type=node_data.get("entityType", "outcome_box"),
                name=node_data.get("label", ""),
                description=node_data.get("description"),
                set_id=set_id,
                notation=notation,
                created_by=user_id,
                now=now,
            )
            node_data["entityId"] = element_id

        # Create relationship for each edge
        for edge in canvas_data.get("edges", []):
            source_eid = node_element_map.get(edge.get("source", ""))
            target_eid = node_element_map.get(edge.get("target", ""))
            if source_eid and target_eid:
                rel_id = str(uuid.uuid4())
                edge_data = edge.get("data", {})

                await materialise_relationship(
                    db,
                    rel_id=rel_id,
                    source_element_id=source_eid,
                    target_element_id=target_eid,
                    relationship_type=edge_data.get("relationshipType", "causal_link"),
                    label="",
                    description="",
                    created_by=user_id,
                    now=now,
                )
                edge_data["relationshipId"] = rel_id

        # Update diagram_versions with enriched canvas data
        await db.execute(
            "UPDATE diagram_versions SET data = ? WHERE diagram_id = ? AND version = 1",
            (json.dumps(canvas_data), diagram_id),
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

    # Phase 3: convert sequence diagrams to the specialised render shape
    # (ADR-132). The generic `{nodes, edges}` canvas format is not rendered by
    # the sequence-diagram page — it expects `{participants, messages,
    # activations}` per frontend/src/lib/canvas/sequence/types.ts. Translate
    # in-place while preserving the original nodes/edges so the materialised
    # elements/relationships keep their UI linkage.
    for diagram_id, canvas_data, diag_def in zip(
        diagram_ids, canvas_data_list, diagrams_def
    ):
        if diag_def.get("diagram_type") != "sequence":
            continue
        seq_data = _nodes_edges_to_sequence(canvas_data)
        # Merge (don't replace) so the page can still fall back to nodes/edges
        # for downstream tooling that expects the generic shape.
        merged = {**canvas_data, **seq_data}
        await db.execute(
            "UPDATE diagram_versions SET data = ? WHERE diagram_id = ? AND version = 1",
            (json.dumps(merged), diagram_id),
        )

    await db.commit()
    return diagram_ids


_SEQUENCE_PARTICIPANT_TYPE_MAP = {
    # Simple / UML element types that commonly appear in sequence diagrams.
    "actor": "actor",
    "person": "actor",
    "component": "component",
    "component_uml": "component",
    "class": "component",
    "object": "component",
    "interface": "service",
    "interface_uml": "service",
    "service": "service",
    "container": "service",
}


def _nodes_edges_to_sequence(canvas_data: dict) -> dict:
    """Translate `{nodes, edges}` into `{participants, messages, activations}`.

    Participant ordering follows node declaration order — the AI prompt places
    lifelines left-to-right in node order, so we preserve that.
    """
    participants: list[dict] = []
    for node in canvas_data.get("nodes", []):
        node_data = node.get("data", {})
        entity_type = node_data.get("entityType") or node.get("type") or "actor"
        participants.append({
            "id": node.get("id", ""),
            "name": node_data.get("label", ""),
            "type": _SEQUENCE_PARTICIPANT_TYPE_MAP.get(entity_type, "component"),
            "entityId": node_data.get("entityId"),
        })

    messages: list[dict] = []
    for order, edge in enumerate(canvas_data.get("edges", [])):
        edge_data = edge.get("data", {})
        messages.append({
            "id": edge.get("id", f"msg-{order}"),
            "from": edge.get("source", ""),
            "to": edge.get("target", ""),
            "label": edge_data.get("label") or edge.get("id", ""),
            "type": "sync",
            "order": order,
        })

    return {
        "participants": participants,
        "messages": messages,
        "activations": [],
    }


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
        description = ai_node.get("description", "")
        if description:
            node_data["description"] = description
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
