"""Canvas-data shape normalization (ADR-218, issue #238).

The shared creation prompt (``backend/app/seed/creation_prompts.py``)
teaches models the *flat* AI/MCP node shape::

    {"id", "type", "label", "position", "size", "visual"}

That shape is consumed by ``apply_diagram_creation`` →
``_build_canvas_nodes`` (``app/ai/creation.py``), which converts it into
the Svelte-Flow *canvas* shape the frontend canvas requires::

    {"id", "type", "position", "width", "height",
     "data": {"label", "entityType", ...}}

But ``create_diagram`` (ADR-162) persists its ``data`` payload verbatim.
A model that follows the creation prompt and then saves via
``create_diagram`` stored flat nodes with no ``data`` object, so
``UnifiedCanvas.svelte`` crashed reading ``n.data.entityType`` and the
diagram "failed to load" (issue #238).

This module is the single authority for the flat → canvas transform.
``normalize_canvas_data`` is shape-detecting and idempotent: nodes/edges
that already carry a dict ``data`` are returned untouched, so it is safe
to apply on write (``create_diagram`` / ``update_diagram``), on read
(``get_diagram`` auto-heal), in the targeted repair script, and
repeatedly. ``app/ai/creation.py`` delegates its per-item conversion
here too (protocols §13 DRY).
"""

from __future__ import annotations

from typing import Any

DEFAULT_NODE_WIDTH = 200
DEFAULT_NODE_HEIGHT = 86

# Top-level keys relocated into `data`/`width`/`height` during conversion.
_RELOCATED_NODE_KEYS = ("label", "size", "visual", "description")


def flat_node_to_canvas(node: dict, *, default_entity_type: str = "") -> dict:
    """Convert a single flat AI node into Svelte-Flow canvas shape.

    Moves ``label`` → ``data.label``, ``type`` → ``data.entityType``,
    ``size`` → top-level ``width``/``height``, and a non-empty ``visual``
    / ``description`` into ``data``. Unknown top-level structural keys
    (e.g. ``parentId``) are preserved. ``default_entity_type`` is used
    when the node has no ``type`` (the doview apply path passes
    ``"outcome_box"``).
    """
    entity_type = node.get("type") or default_entity_type
    label = node.get("label", "")
    size = node.get("size") or {}
    visual = node.get("visual")
    description = node.get("description")

    data: dict[str, Any] = {"label": label, "entityType": entity_type}
    if description:
        data["description"] = description
    if visual:
        data["visual"] = visual

    out = {k: v for k, v in node.items() if k not in _RELOCATED_NODE_KEYS}
    out["type"] = entity_type
    out["data"] = data
    out.setdefault("position", {"x": 0, "y": 0})
    if "width" not in out:
        out["width"] = size.get("width", DEFAULT_NODE_WIDTH)
    if "height" not in out:
        out["height"] = size.get("height", DEFAULT_NODE_HEIGHT)
    return out


def flat_edge_to_canvas(edge: dict, *, default_relationship_type: str = "") -> dict:
    """Convert a single flat AI edge into Svelte-Flow canvas shape.

    Moves ``type`` → ``data.relationshipType`` (keeping ``type`` for the
    edge renderer), a non-empty ``visual`` into ``data``, and adds the
    ``center`` handles the canvas uses for AI-authored edges.
    """
    rel_type = edge.get("type") or default_relationship_type
    visual = edge.get("visual")

    data: dict[str, Any] = {"relationshipType": rel_type}
    if visual:
        data["visual"] = visual

    out = {k: v for k, v in edge.items() if k != "visual"}
    out["type"] = rel_type
    out["data"] = data
    out.setdefault("sourceHandle", "center")
    out.setdefault("targetHandle", "center")
    return out


def _normalize_node(node: Any) -> Any:
    if not isinstance(node, dict):
        return node
    # Already canvas-shaped — leave untouched (idempotent).
    if isinstance(node.get("data"), dict):
        return node
    return flat_node_to_canvas(node)


def _normalize_edge(edge: Any) -> Any:
    if not isinstance(edge, dict):
        return edge
    if isinstance(edge.get("data"), dict):
        return edge
    return flat_edge_to_canvas(edge)


def needs_normalization(data: Any) -> bool:
    """True iff ``data`` contains at least one flat node or edge.

    Lets callers (e.g. the repair script) skip a rewrite when the
    payload is already canvas-shaped.
    """
    if not isinstance(data, dict):
        return False
    nodes = data.get("nodes")
    edges = data.get("edges")
    if isinstance(nodes, list) and any(
        isinstance(n, dict) and not isinstance(n.get("data"), dict) for n in nodes
    ):
        return True
    return bool(
        isinstance(edges, list)
        and any(
            isinstance(e, dict) and not isinstance(e.get("data"), dict) for e in edges
        )
    )


def normalize_canvas_data(data: Any) -> Any:
    """Return ``data`` with any flat nodes/edges converted to canvas shape.

    Shape-detecting and idempotent. Non-dict payloads and dicts without
    ``nodes``/``edges`` lists (markdown ``{content}``, sequence
    ``{participants, ...}``) are returned unchanged. The input is not
    mutated — a shallow copy is returned when changes apply.
    """
    if not isinstance(data, dict):
        return data
    nodes = data.get("nodes")
    edges = data.get("edges")
    if not isinstance(nodes, list) and not isinstance(edges, list):
        return data

    result = dict(data)
    if isinstance(nodes, list):
        result["nodes"] = [_normalize_node(n) for n in nodes]
    if isinstance(edges, list):
        result["edges"] = [_normalize_edge(e) for e in edges]
    return result
