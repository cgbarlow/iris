"""Compute module for the dynamic_list diagram type (ADR-186).

Renders a markdown bullet list from one of two sources:

- ``diagram_relationships``: emits two bullets per intra-diagram
  relationship (source name, then target name). Non-deduplicated by
  design.
- ``package_elements``: emits one bullet per element belonging to a
  package, sorted alphabetically by name.

The ``show_description`` toggle appends ``(description)`` to each
bullet when set. Missing / empty descriptions fall back to the
no-parens bullet for that single line.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


_PLACEHOLDER = "_No items yet._"


def _bullet(name: str, description: str | None, show_description: bool) -> str:
    if show_description and description is not None and description.strip() != "":
        return f"- **{name}** ({description})"
    # Issue #170: previously emitted ``- **{name}`` with no closing
    # ``**`` — markdown rendered the literal asterisks instead of bolding
    # the name when descriptions were hidden.
    return f"- **{name}**"


async def _fetch_diagram_header(
    db: DatabasePort, diagram_id: str,
) -> str:
    cursor = await db.execute(
        "SELECT dv.name FROM diagrams d "
        "JOIN diagram_versions dv ON d.id = dv.diagram_id "
        "  AND d.current_version = dv.version "
        "WHERE d.id = ? AND d.is_deleted = 0",
        (diagram_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return "# Dynamic List"
    return f"# {row[0] or 'Dynamic List'}"


async def _diagram_element_ids(
    db: DatabasePort, diagram_id: str,
) -> list[str]:
    cursor = await db.execute(
        "SELECT dv.data FROM diagrams d "
        "JOIN diagram_versions dv ON d.id = dv.diagram_id "
        "  AND d.current_version = dv.version "
        "WHERE d.id = ?",
        (diagram_id,),
    )
    row = await cursor.fetchone()
    if not row or not row[0]:
        return []
    try:
        canvas = json.loads(row[0]) if isinstance(row[0], str) else row[0]
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(canvas, dict):
        return []
    ids: list[str] = []
    for node in canvas.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        data = node.get("data") if isinstance(node.get("data"), dict) else None
        if not data:
            continue
        eid = data.get("entityId")
        if isinstance(eid, str):
            ids.append(eid)
    return ids


async def _diagram_relationships_body(
    db: DatabasePort,
    diagram_id: str,
    *,
    show_description: bool,
) -> str:
    """Default mode — two bullets per intra-diagram relationship."""
    element_ids = await _diagram_element_ids(db, diagram_id)
    if not element_ids:
        return _PLACEHOLDER
    placeholders = ",".join("?" for _ in element_ids)
    cursor = await db.execute(
        f"SELECT r.relationship_type, "  # noqa: S608
        f"  sev.name AS source_name, sev.description AS source_desc, "
        f"  tev.name AS target_name, tev.description AS target_desc "
        f"FROM relationships r "
        f"JOIN elements se ON r.source_element_id = se.id "
        f"JOIN element_versions sev ON se.id = sev.element_id "
        f"  AND se.current_version = sev.version "
        f"JOIN elements te ON r.target_element_id = te.id "
        f"JOIN element_versions tev ON te.id = tev.element_id "
        f"  AND te.current_version = tev.version "
        f"WHERE r.is_deleted = 0 "
        f"  AND se.is_deleted = 0 AND te.is_deleted = 0 "
        f"  AND r.source_element_id IN ({placeholders}) "
        f"  AND r.target_element_id IN ({placeholders}) "
        f"ORDER BY sev.name, tev.name, r.relationship_type",
        [*element_ids, *element_ids],
    )
    rows = await cursor.fetchall()
    if not rows:
        return _PLACEHOLDER
    bullets: list[str] = []
    for r in rows:
        source_name = r[1] or "(unnamed)"
        source_desc = r[2]
        target_name = r[3] or "(unnamed)"
        target_desc = r[4]
        bullets.append(_bullet(source_name, source_desc, show_description))
        bullets.append(_bullet(target_name, target_desc, show_description))
    return "\n".join(bullets)


async def _package_elements_body(
    db: DatabasePort,
    package_id: str | None,
    *,
    show_description: bool,
) -> str:
    """Alternative mode — one bullet per element in the package."""
    if not package_id:
        return _PLACEHOLDER
    cursor = await db.execute(
        "SELECT ev.name, ev.description "
        "FROM elements e "
        "JOIN element_versions ev ON e.id = ev.element_id "
        "  AND e.current_version = ev.version "
        "WHERE e.package_id = ? AND e.is_deleted = 0 "
        "ORDER BY LOWER(ev.name) ASC",
        (package_id,),
    )
    rows = await cursor.fetchall()
    if not rows:
        return _PLACEHOLDER
    return "\n".join(
        _bullet(r[0] or "(unnamed)", r[1], show_description)
        for r in rows
    )


async def compute_dynamic_list_content(
    db: DatabasePort,
    diagram_id: str,
    *,
    mode: str,
    package_id: str | None,
    show_description: bool,
) -> str:
    """Return the synthesised markdown for a dynamic_list diagram (ADR-186)."""
    header = await _fetch_diagram_header(db, diagram_id)
    if mode == "package_elements":
        body = await _package_elements_body(
            db, package_id, show_description=show_description,
        )
    else:  # default: diagram_relationships
        body = await _diagram_relationships_body(
            db, diagram_id, show_description=show_description,
        )
    # Issue #170(a): no auto-generated footer — the markdown now ends at
    # the body so the user-visible content is uncluttered.
    return f"{header}\n\n{body}\n"
