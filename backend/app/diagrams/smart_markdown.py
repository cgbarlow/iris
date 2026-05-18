"""Compute module for the smart_markdown diagram type (ADR-205, issue #185).

Resolves inline-reference tokens in user-edited markdown source against
live Iris entity fields. The user writes markdown with tokens of the form

    {{<entity-type>:<id>:<field-spec>}}

where ``entity-type`` is one of ``element``, ``package``, ``diagram``,
``set``, ``collection``; ``id`` is the entity's GUID; and ``field-spec``
is ``name``, ``description``, or (for elements only) ``attr:<key>``
where ``<key>`` is a key in the element's ``data`` JSON.

Unresolvable tokens (entity not found, deleted, wrong field for the
entity type, missing attribute) render as ``~~{{...}}~~`` so the user
sees them — silent drops would hide data loss.

Resolution happens at GET time via ``_maybe_synthesise_content`` in
``backend/app/diagrams/service.py`` (ADR-187 hook). Resolved markdown
lands in ``data.content`` so the existing markdown / docx / pdf
rendering pipeline consumes it unchanged (Protocol §13 DRY).
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


_PLACEHOLDER = "_No content yet._"

# entity-type, id, field-spec. ID rejects ``:`` and ``}`` so multi-segment
# field-specs (``attr:<key>``) bind to the third group only.
_TOKEN_RE = re.compile(
    r"\{\{(element|package|diagram|set|collection):"
    r"([^:}]+):"
    r"((?:attr:[^}]+)|name|description)\}\}"
)


async def _read_source(db: DatabasePort, diagram_id: str) -> str:
    """Return ``data.markdown_source`` for the diagram, or '' if missing."""
    cursor = await db.execute(
        "SELECT dv.data FROM diagrams d "
        "JOIN diagram_versions dv ON d.id = dv.diagram_id "
        "  AND d.current_version = dv.version "
        "WHERE d.id = ? AND d.is_deleted = 0",
        (diagram_id,),
    )
    row = await cursor.fetchone()
    if not row or not row[0]:
        return ""
    try:
        data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
    except (json.JSONDecodeError, TypeError):
        return ""
    if not isinstance(data, dict):
        return ""
    src = data.get("markdown_source")
    return src if isinstance(src, str) else ""


async def _fetch_element_field(
    db: DatabasePort, entity_id: str, field_spec: str,
) -> str | None:
    cursor = await db.execute(
        "SELECT ev.name, ev.description, ev.data FROM elements e "
        "JOIN element_versions ev ON e.id = ev.element_id "
        "  AND e.current_version = ev.version "
        "WHERE e.id = ? AND e.is_deleted = 0",
        (entity_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return None
    if field_spec == "name":
        return row[0]
    if field_spec == "description":
        return row[1]
    if field_spec.startswith("attr:"):
        key = field_spec[len("attr:"):]
        raw = row[2]
        if raw is None:
            return None
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            return None
        if not isinstance(data, dict):
            return None
        val = data.get(key)
        if val is None:
            return None
        return str(val)
    return None


async def _fetch_named_field(
    db: DatabasePort,
    *,
    table: str,
    versions_table: str,
    fk: str,
    entity_id: str,
    field_spec: str,
) -> str | None:
    if field_spec not in ("name", "description"):
        return None
    cursor = await db.execute(
        f"SELECT v.name, v.description FROM {table} t "  # noqa: S608
        f"JOIN {versions_table} v ON t.id = v.{fk} "
        f"  AND t.current_version = v.version "
        f"WHERE t.id = ? AND t.is_deleted = 0",
        (entity_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return None
    return row[0] if field_spec == "name" else row[1]


async def _fetch_set_field(
    db: DatabasePort, entity_id: str, field_spec: str,
) -> str | None:
    if field_spec not in ("name", "description"):
        return None
    cursor = await db.execute(
        "SELECT name, description FROM sets WHERE id = ? AND is_deleted = 0",
        (entity_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return None
    return row[0] if field_spec == "name" else row[1]


async def _fetch_collection_field(
    db: DatabasePort, entity_id: str, field_spec: str,
) -> str | None:
    if field_spec not in ("name", "description"):
        return None
    cursor = await db.execute(
        "SELECT name, description FROM collections WHERE id = ?",
        (entity_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return None
    return row[0] if field_spec == "name" else row[1]


async def _resolve_one(
    db: DatabasePort, entity_type: str, entity_id: str, field_spec: str,
) -> str | None:
    """Return the resolved value, or None if unresolvable.

    None signals: entity missing / deleted, field invalid for the type,
    or attribute key missing. Callers turn None into strikethrough.
    """
    if entity_type == "element":
        return await _fetch_element_field(db, entity_id, field_spec)
    if entity_type == "package":
        return await _fetch_named_field(
            db, table="packages", versions_table="package_versions",
            fk="package_id", entity_id=entity_id, field_spec=field_spec,
        )
    if entity_type == "diagram":
        return await _fetch_named_field(
            db, table="diagrams", versions_table="diagram_versions",
            fk="diagram_id", entity_id=entity_id, field_spec=field_spec,
        )
    if entity_type == "set":
        return await _fetch_set_field(db, entity_id, field_spec)
    if entity_type == "collection":
        return await _fetch_collection_field(db, entity_id, field_spec)
    return None


async def compute_smart_markdown_content(
    db: DatabasePort, diagram_id: str,
) -> str:
    """Return the resolved markdown for a smart_markdown diagram (ADR-205)."""
    source = await _read_source(db, diagram_id)
    if not source.strip():
        return _PLACEHOLDER

    matches = list(_TOKEN_RE.finditer(source))
    if not matches:
        return source

    out: list[str] = []
    cursor = 0
    for m in matches:
        out.append(source[cursor:m.start()])
        entity_type, entity_id, field_spec = m.group(1), m.group(2), m.group(3)
        resolved = await _resolve_one(db, entity_type, entity_id, field_spec)
        if resolved is None or resolved == "":
            out.append(f"~~{m.group(0)}~~")
        else:
            out.append(resolved)
        cursor = m.end()
    out.append(source[cursor:])
    return "".join(out)
