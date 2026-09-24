"""Which elements a diagram's canvas draws (ADR-248).

A canvas node that represents a model element carries the element's id
in ``node.data.entityId``. This used to be extracted inline in
``get_diagram_relationships`` (ADR-184); it is shared here by that route
and ``GET /api/diagrams/{id}/elements``.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


def canvas_entity_ids(canvas: object) -> list[str]:
    """Return the distinct element ids referenced by a canvas's nodes.

    ``canvas`` is the stored diagram data, either as its JSON string or
    already decoded. Order is canvas order, keeping each id's first
    occurrence. Nodes without a non-empty string ``data.entityId`` are
    skipped; a missing or malformed canvas yields ``[]``.
    """
    if isinstance(canvas, str):
        try:
            canvas = json.loads(canvas) if canvas else None
        except ValueError:
            return []
    if not isinstance(canvas, dict):
        return []
    nodes = canvas.get("nodes")
    if not isinstance(nodes, list):
        return []

    seen: set[str] = set()
    ids: list[str] = []
    for node in nodes:
        node_data = node.get("data") if isinstance(node, dict) else None
        if not isinstance(node_data, dict):
            continue
        eid = node_data.get("entityId")
        if isinstance(eid, str) and eid and eid not in seen:
            seen.add(eid)
            ids.append(eid)
    return ids


async def get_canvas_entity_ids(
    db: DatabasePort,
    diagram_id: str,
) -> list[str] | None:
    """Element ids on a live diagram's current canvas, in one query.

    Returns ``None`` when the diagram does not exist or is soft-deleted,
    so callers can answer 404 without a separate existence check.
    """
    cursor = await db.execute(
        "SELECT dv.data FROM diagrams d "
        "JOIN diagram_versions dv ON d.id = dv.diagram_id "
        "  AND d.current_version = dv.version "
        "WHERE d.id = ? AND d.is_deleted = 0",
        (diagram_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return canvas_entity_ids(row[0])
