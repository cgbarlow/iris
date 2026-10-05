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

ADR-260 (issue #315) adds class members to the same transform. The
canvas reads them from ``data.attributes`` / ``data.operations`` /
``data.literals``; older creation prompts wrote them under
``data.compartments``, so ``normalize_canvas_data`` lifts them.
"""

from __future__ import annotations

from typing import Any

DEFAULT_NODE_WIDTH = 200
DEFAULT_NODE_HEIGHT = 86

# Top-level keys relocated into `data`/`width`/`height` during conversion.
_RELOCATED_NODE_KEYS = ("label", "size", "visual", "description")

# Class-member keys the canvas reads straight from a node's `data`.
_MEMBER_KEYS = ("attributes", "operations", "literals")


def _lift_compartments(data: dict) -> dict:
    """Move ``data.compartments.{attributes, operations, literals}`` up
    into ``data`` (ADR-260).

    A key ``data`` already has wins over the one in ``compartments``.
    Other keys in ``compartments`` stay there. Returns ``data`` itself
    when there is nothing to lift, so callers can test identity.
    """
    compartments = data.get("compartments")
    if not isinstance(compartments, dict):
        return data
    members = {
        key: compartments[key]
        for key in _MEMBER_KEYS
        if isinstance(compartments.get(key), list)
    }
    if not members:
        return data
    out = {**members, **data}
    rest = {k: v for k, v in compartments.items() if k not in members}
    if rest:
        out["compartments"] = rest
    else:
        del out["compartments"]
    return out


def _is_flat_node(node: dict) -> bool:
    """True for a node in the flat AI/MCP shape.

    A flat node normally has no ``data`` object. The UML creation prompt
    adds one that carries only the class members, next to a top-level
    ``label``; that node is still flat (ADR-260).
    """
    data = node.get("data")
    if not isinstance(data, dict):
        return True
    return "label" in node and "label" not in data


def flat_node_to_canvas(node: dict, *, default_entity_type: str = "") -> dict:
    """Convert a single flat AI node into Svelte-Flow canvas shape.

    Moves ``label`` → ``data.label``, ``type`` → ``data.entityType``,
    ``size`` → top-level ``width``/``height``, and a non-empty ``visual``
    / ``description`` into ``data``. Unknown top-level structural keys
    (e.g. ``parentId``) are preserved. ``default_entity_type`` is used
    when the node has no ``type`` (the doview apply path passes
    ``"outcome_box"``). Keys the node already has under ``data`` (class
    members, ADR-260) are kept.
    """
    own_data = node.get("data")
    data: dict[str, Any] = dict(own_data) if isinstance(own_data, dict) else {}
    entity_type = node.get("type") or data.get("entityType") or default_entity_type
    size = node.get("size") or {}
    visual = node.get("visual")
    description = node.get("description")

    data["label"] = node.get("label", data.get("label", ""))
    data["entityType"] = entity_type
    if description:
        data["description"] = description
    if visual:
        data["visual"] = visual

    out = {k: v for k, v in node.items() if k not in _RELOCATED_NODE_KEYS}
    out["type"] = entity_type
    out["data"] = _lift_compartments(data)
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
    if _is_flat_node(node):
        return flat_node_to_canvas(node)
    # Already canvas-shaped — untouched unless it carries compartments.
    data = _lift_compartments(node["data"])
    return node if data is node["data"] else {**node, "data": data}


def _node_needs_normalization(node: Any) -> bool:
    if not isinstance(node, dict):
        return False
    return _is_flat_node(node) or _lift_compartments(node["data"]) is not node["data"]


def _normalize_edge(edge: Any) -> Any:
    if not isinstance(edge, dict):
        return edge
    if isinstance(edge.get("data"), dict):
        return edge
    return flat_edge_to_canvas(edge)


def needs_normalization(data: Any) -> bool:
    """True iff ``data`` contains at least one flat node or edge, or a
    node whose class members are still under ``data.compartments``.

    Lets callers (e.g. the repair script) skip a rewrite when the
    payload is already canvas-shaped.
    """
    if not isinstance(data, dict):
        return False
    nodes = data.get("nodes")
    edges = data.get("edges")
    if isinstance(nodes, list) and any(_node_needs_normalization(n) for n in nodes):
        return True
    return bool(
        isinstance(edges, list)
        and any(
            isinstance(e, dict) and not isinstance(e.get("data"), dict) for e in edges
        )
    )


def normalize_canvas_data(data: Any) -> Any:
    """Return ``data`` with any flat nodes/edges converted to canvas shape
    and class members lifted out of ``data.compartments``.

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
