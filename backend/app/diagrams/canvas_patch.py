"""Pure canvas-patch engine (ADR-252, SPEC-252-A, issue #301).

Applies an ordered list of operations to a diagram's Svelte-Flow canvas
(``{"nodes": [...], "edges": [...], ...}``) in memory and returns the new
canvas plus one result per operation. It does no I/O: the service
(``app.diagrams.service.patch_diagram``) pre-fetches, in one batched query
each, the elements and relationships the operations refer to
(:func:`referenced_ids` says which) and passes them in a
:class:`PatchContext`. The new canvas is then persisted through the normal
``update_diagram`` path, so a patch stores exactly what a full update with
the same canvas would.

Operations (each a JSON object with an ``op`` key):

``add_node``     ``node``: a full node (canvas or flat AI shape, ADR-218).
                 Rejected if its id exists, it has no numeric position, its
                 ``parentId`` names no node, or its ``data.entityId`` is not a
                 live element in the diagram's set.
``update_node``  ``id`` plus any of ``position`` (partial), ``width``,
                 ``height``, ``type``, ``data`` (shallow merge; ``null``
                 removes a key). A changed ``data.entityId`` is validated as
                 for ``add_node``.
``remove_node``  ``id``, ``cascade_edges`` (default true: connected edges go
                 too; false: rejected while edges connect it). Rejected
                 while other nodes are nested in it (``parentId``).
``add_edge``     ``edge``: a full edge. ``source`` / ``target`` must be
                 existing nodes; a ``data.relationshipId`` must name a live
                 relationship between the two nodes' elements, either way.
``update_edge``  ``id`` plus any of ``data`` (shallow merge as above),
                 ``sourceHandle``, ``targetHandle``, ``type``. A changed
                 ``data.relationshipId`` is validated as for ``add_edge``.
``remove_edge``  ``id``.
``sync_labels``  optional ``node_ids`` (default: every node). Sets each
                 node's ``data.label`` to its element's current name and
                 touches nothing else (the diagram owns presentation,
                 ADR-230 F1). Nodes whose element is gone are ``skipped``.

The input canvas is never mutated; any failure raises
:class:`CanvasPatchError` naming the operation's index, so a caller that
only writes on success writes nothing on failure.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from app.diagrams.canvas_entities import canvas_entity_ids
from app.diagrams.canvas_normalize import normalize_canvas_data

MAX_OPERATIONS = 200

_NODE_UPDATE_FIELDS = frozenset({"position", "width", "height", "type", "data"})
_EDGE_UPDATE_FIELDS = frozenset({"data", "sourceHandle", "targetHandle", "type"})


@dataclass(frozen=True)
class ElementRef:
    """What the engine needs to know about a live element."""

    name: str
    set_id: str | None


@dataclass(frozen=True)
class PatchContext:
    """Pre-fetched lookups for validating and applying a patch.

    ``elements`` holds the live (not soft-deleted) elements among the ids
    :func:`referenced_ids` returned; ``relationships`` maps each live
    relationship id among them to its ``(source_element_id,
    target_element_id)``. Anything absent is treated as missing/deleted.
    """

    set_id: str | None
    elements: Mapping[str, ElementRef] = field(default_factory=dict)
    relationships: Mapping[str, tuple[str, str]] = field(default_factory=dict)


@dataclass(frozen=True)
class PatchOutcome:
    """The patched canvas and one result dict per operation, in order."""

    data: dict[str, Any]
    results: list[dict[str, Any]]


class CanvasPatchError(ValueError):
    """A patch can't be applied. ``op_index`` / ``op`` name the failing
    operation; both are ``None`` when the patch as a whole is invalid (for
    example the diagram isn't a node/edge canvas)."""

    def __init__(self, message: str, *, op_index: int | None = None,
                 op: str | None = None) -> None:
        self.message = message
        self.op_index = op_index
        self.op = op
        prefix = "" if op_index is None else f"operations[{op_index}] ({op or '?'}): "
        super().__init__(prefix + message)


class _OpError(Exception):
    """Raised inside an op handler; wrapped with the op index by the loop."""


# ── Public API ───────────────────────────────────────────────────────


def referenced_ids(
    data: Any, operations: Any,
) -> tuple[list[str], list[str]]:
    """Element and relationship ids the service must fetch for ``operations``.

    Element ids: every ``data.entityId`` an ``add_node`` / ``update_node``
    sets, plus — only when a ``sync_labels`` op is present — every element
    on the current canvas. Relationship ids: every ``data.relationshipId``
    an ``add_edge`` / ``update_edge`` sets. Malformed operations are
    skipped here; :func:`apply_operations` reports them.
    """
    elements: list[str] = []
    relationships: list[str] = []
    ops = operations if isinstance(operations, list) else []
    for op in ops:
        if not isinstance(op, dict):
            continue
        kind = op.get("op")
        if kind == "add_node":
            elements.append(_data_value(op.get("node"), "entityId"))
        elif kind == "update_node":
            elements.append(_data_value(op, "entityId"))
        elif kind == "add_edge":
            relationships.append(_data_value(op.get("edge"), "relationshipId"))
        elif kind == "update_edge":
            relationships.append(_data_value(op, "relationshipId"))
        elif kind == "sync_labels":
            elements.extend(canvas_entity_ids(data))
    return _distinct(elements), _distinct(relationships)


def apply_operations(
    data: Any, operations: Any, ctx: PatchContext,
) -> PatchOutcome:
    """Apply ``operations`` in order to a copy of ``data``.

    Returns the patched canvas (other top-level keys such as ``viewport``
    are kept) and a result per operation. Raises :class:`CanvasPatchError`
    on the first failing operation; ``data`` is never mutated.
    """
    if not isinstance(operations, list) or not 1 <= len(operations) <= MAX_OPERATIONS:
        raise CanvasPatchError(
            f"operations must be a list of 1 to {MAX_OPERATIONS} items",
        )
    canvas = _canvas_copy(data)
    results: list[dict[str, Any]] = []
    for index, op in enumerate(operations):
        kind = op.get("op") if isinstance(op, dict) else None
        handler = _HANDLERS.get(kind) if isinstance(kind, str) else None
        if handler is None:
            if not isinstance(op, dict) or not isinstance(kind, str):
                message = "each operation must be an object with an 'op' field"
            else:
                message = (
                    f"unknown op {kind!r}; expected one of "
                    + ", ".join(sorted(_HANDLERS))
                )
            raise CanvasPatchError(message, op_index=index,
                                   op=kind if isinstance(kind, str) else None)
        try:
            result = handler(canvas, op, ctx)
        except _OpError as exc:
            raise CanvasPatchError(str(exc), op_index=index, op=kind) from None
        results.append({"index": index, "op": kind, **result})
    return PatchOutcome(data=canvas, results=results)


# ── Canvas helpers ───────────────────────────────────────────────────


def _canvas_copy(data: Any) -> dict[str, Any]:
    """Deep-copied, canvas-shaped ``data`` with ``nodes`` / ``edges`` lists.

    An empty payload is an empty canvas. Anything that isn't a node/edge
    canvas (markdown ``{content}``, sequence ``{participants, ...}``) is
    rejected rather than grown into a hybrid.
    """
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise CanvasPatchError("diagram data is not a node/edge canvas")
    nodes = data.get("nodes")
    edges = data.get("edges")
    if (nodes is None and edges is None and data) or \
            (nodes is not None and not isinstance(nodes, list)) or \
            (edges is not None and not isinstance(edges, list)):
        raise CanvasPatchError(
            "diagram data is not a node/edge canvas; patch_diagram only edits "
            "{nodes, edges} diagrams — use update_diagram for this one",
        )
    canvas = copy.deepcopy(normalize_canvas_data(data))
    canvas["nodes"] = canvas.get("nodes") or []
    canvas["edges"] = canvas.get("edges") or []
    return canvas


def _normalised(key: str, item: dict[str, Any]) -> dict[str, Any]:
    """A deep copy of a new node / edge in canvas shape (ADR-218 flat AI
    shapes are converted exactly as ``update_diagram`` would convert them)."""
    try:
        return copy.deepcopy(normalize_canvas_data({key: [item]})[key][0])
    except (AttributeError, TypeError) as exc:
        raise _OpError(f"malformed {key[:-1]}: {exc}") from None


def _find(items: list[Any], item_id: str) -> int | None:
    for i, item in enumerate(items):
        if isinstance(item, dict) and item.get("id") == item_id:
            return i
    return None


def _node_at(canvas: dict[str, Any], node_id: str) -> dict[str, Any]:
    i = _find(canvas["nodes"], node_id)
    if i is None:
        raise _OpError(f"node {node_id!r} does not exist")
    return canvas["nodes"][i]


def _edge_at(canvas: dict[str, Any], edge_id: str) -> dict[str, Any]:
    i = _find(canvas["edges"], edge_id)
    if i is None:
        raise _OpError(f"edge {edge_id!r} does not exist")
    return canvas["edges"][i]


def _data_value(item: Any, key: str) -> Any:
    data = item.get("data") if isinstance(item, dict) else None
    return data.get(key) if isinstance(data, dict) else None


def _distinct(values: list[Any]) -> list[str]:
    return list(dict.fromkeys(v for v in values if isinstance(v, str) and v))


def _required_id(op: dict[str, Any], key: str = "id") -> str:
    value = op.get(key)
    if not isinstance(value, str) or not value:
        raise _OpError(f"'{key}' must be a non-empty string")
    return value


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_fields(op: dict[str, Any], allowed: frozenset[str]) -> None:
    unknown = sorted(set(op) - allowed - {"op", "id"})
    if unknown:
        raise _OpError(
            f"unknown field(s) {', '.join(map(repr, unknown))}; can change "
            + ", ".join(sorted(allowed)),
        )


def _merge_data(target: dict[str, Any], patch: Any) -> None:
    """Shallow-merge ``patch`` into ``target['data']``; ``None`` deletes."""
    if not isinstance(patch, dict):
        raise _OpError("'data' must be an object")
    data = target.get("data")
    merged = dict(data) if isinstance(data, dict) else {}
    for key, value in patch.items():
        if value is None:
            merged.pop(key, None)
        else:
            merged[key] = value
    target["data"] = merged


def _check_entity(entity_id: Any, ctx: PatchContext) -> None:
    if entity_id is None:
        return
    if not isinstance(entity_id, str) or not entity_id:
        raise _OpError("data.entityId must be a non-empty string")
    element = ctx.elements.get(entity_id)
    if element is None:
        raise _OpError(f"element {entity_id!r} does not exist or is deleted")
    if element.set_id != ctx.set_id:
        raise _OpError(
            f"element {entity_id!r} is not in this diagram's set; add elements "
            "from the diagram's own set",
        )


def _check_relationship(canvas: dict[str, Any], edge: dict[str, Any],
                        ctx: PatchContext) -> None:
    rel_id = _data_value(edge, "relationshipId")
    if rel_id is None:
        return
    if not isinstance(rel_id, str) or not rel_id:
        raise _OpError("data.relationshipId must be a non-empty string")
    endpoints = ctx.relationships.get(rel_id)
    if endpoints is None:
        raise _OpError(f"relationship {rel_id!r} does not exist or is deleted")
    ends = {
        _data_value(_node_at(canvas, edge["source"]), "entityId"),
        _data_value(_node_at(canvas, edge["target"]), "entityId"),
    }
    if set(endpoints) != ends:
        raise _OpError(
            f"relationship {rel_id!r} does not connect the elements of nodes "
            f"{edge['source']!r} and {edge['target']!r}",
        )


# ── Op handlers ──────────────────────────────────────────────────────


def _add_node(canvas: dict[str, Any], op: dict[str, Any],
              ctx: PatchContext) -> dict[str, Any]:
    raw = op.get("node")
    if not isinstance(raw, dict):
        raise _OpError("'node' must be a node object")
    node = _normalised("nodes", raw)
    node_id = _required_id(node)
    if _find(canvas["nodes"], node_id) is not None:
        raise _OpError(f"node {node_id!r} already exists")
    position = node.get("position")
    if not (isinstance(position, dict) and _is_number(position.get("x"))
            and _is_number(position.get("y"))):
        raise _OpError("node needs a position with numeric x and y")
    parent = node.get("parentId")
    if parent is not None and (not isinstance(parent, str)
                               or _find(canvas["nodes"], parent) is None):
        raise _OpError(f"parent node {parent!r} does not exist")
    _check_entity(_data_value(node, "entityId"), ctx)
    canvas["nodes"].append(node)
    return {"id": node_id}


def _update_node(canvas: dict[str, Any], op: dict[str, Any],
                 ctx: PatchContext) -> dict[str, Any]:
    node_id = _required_id(op)
    _check_fields(op, _NODE_UPDATE_FIELDS)
    node = _node_at(canvas, node_id)
    old_entity = _data_value(node, "entityId")
    if "position" in op:
        position = op["position"]
        if not isinstance(position, dict) or not set(position) <= {"x", "y"} or \
                not all(_is_number(v) for v in position.values()):
            raise _OpError("'position' must be an object with numeric x and/or y")
        current = node.get("position")
        node["position"] = {**(current if isinstance(current, dict) else {}), **position}
    for key in ("width", "height"):
        if key in op:
            if not _is_number(op[key]):
                raise _OpError(f"'{key}' must be a number")
            node[key] = op[key]
    if "type" in op:
        if not isinstance(op["type"], str) or not op["type"]:
            raise _OpError("'type' must be a non-empty string")
        node["type"] = op["type"]
    if "data" in op:
        _merge_data(node, op["data"])
        new_entity = _data_value(node, "entityId")
        if new_entity != old_entity:
            _check_entity(new_entity, ctx)
    return {"id": node_id}


def _remove_node(canvas: dict[str, Any], op: dict[str, Any],
                 _ctx: PatchContext) -> dict[str, Any]:
    node_id = _required_id(op)
    cascade = op.get("cascade_edges", True)
    if not isinstance(cascade, bool):
        raise _OpError("'cascade_edges' must be true or false")
    index = _find(canvas["nodes"], node_id)
    if index is None:
        raise _OpError(f"node {node_id!r} does not exist")
    children = [n.get("id") for n in canvas["nodes"]
                if isinstance(n, dict) and n.get("parentId") == node_id]
    if children:
        raise _OpError(
            f"node {node_id!r} contains nested nodes {children}; remove them first",
        )
    connected = [e.get("id") for e in canvas["edges"] if isinstance(e, dict)
                 and node_id in (e.get("source"), e.get("target"))]
    if connected and not cascade:
        raise _OpError(
            f"node {node_id!r} has connected edges {connected}; remove them or "
            "set cascade_edges to true",
        )
    del canvas["nodes"][index]
    canvas["edges"] = [e for e in canvas["edges"] if not (
        isinstance(e, dict) and node_id in (e.get("source"), e.get("target"))
    )]
    return {"id": node_id, "removed_edges": connected}


def _add_edge(canvas: dict[str, Any], op: dict[str, Any],
              ctx: PatchContext) -> dict[str, Any]:
    raw = op.get("edge")
    if not isinstance(raw, dict):
        raise _OpError("'edge' must be an edge object")
    edge = _normalised("edges", raw)
    edge_id = _required_id(edge)
    if _find(canvas["edges"], edge_id) is not None:
        raise _OpError(f"edge {edge_id!r} already exists")
    for end in ("source", "target"):
        _node_at(canvas, _required_id(edge, end))
    _check_relationship(canvas, edge, ctx)
    canvas["edges"].append(edge)
    return {"id": edge_id}


def _update_edge(canvas: dict[str, Any], op: dict[str, Any],
                 ctx: PatchContext) -> dict[str, Any]:
    edge_id = _required_id(op)
    _check_fields(op, _EDGE_UPDATE_FIELDS)
    edge = _edge_at(canvas, edge_id)
    old_rel = _data_value(edge, "relationshipId")
    for key in ("sourceHandle", "targetHandle", "type"):
        if key in op:
            value = op[key]
            if value is not None and not isinstance(value, str):
                raise _OpError(f"'{key}' must be a string or null")
            edge[key] = value
    if "data" in op:
        _merge_data(edge, op["data"])
        if _data_value(edge, "relationshipId") != old_rel:
            _check_relationship(canvas, edge, ctx)
    return {"id": edge_id}


def _remove_edge(canvas: dict[str, Any], op: dict[str, Any],
                 _ctx: PatchContext) -> dict[str, Any]:
    edge_id = _required_id(op)
    index = _find(canvas["edges"], edge_id)
    if index is None:
        raise _OpError(f"edge {edge_id!r} does not exist")
    del canvas["edges"][index]
    return {"id": edge_id}


def _sync_labels(canvas: dict[str, Any], op: dict[str, Any],
                 ctx: PatchContext) -> dict[str, Any]:
    _check_fields(op, frozenset({"node_ids"}))
    node_ids = op.get("node_ids")
    if node_ids is None:
        targets = [n for n in canvas["nodes"] if isinstance(n, dict)]
    else:
        if not isinstance(node_ids, list) or not all(
            isinstance(i, str) and i for i in node_ids
        ):
            raise _OpError("'node_ids' must be a list of node ids")
        targets = [_node_at(canvas, i) for i in dict.fromkeys(node_ids)]
    changed: list[str] = []
    skipped: list[str] = []
    for node in targets:
        entity_id = _data_value(node, "entityId")
        if not entity_id:
            continue
        element = ctx.elements.get(entity_id)
        if element is None:
            skipped.append(node.get("id"))
            continue
        if node["data"].get("label") != element.name:
            node["data"]["label"] = element.name
            changed.append(node.get("id"))
    return {"ids": changed, "skipped": skipped}


_Handler = Callable[[dict[str, Any], dict[str, Any], PatchContext], dict[str, Any]]

_HANDLERS: dict[str, _Handler] = {
    "add_node": _add_node,
    "update_node": _update_node,
    "remove_node": _remove_node,
    "add_edge": _add_edge,
    "update_edge": _update_edge,
    "remove_edge": _remove_edge,
    "sync_labels": _sync_labels,
}
