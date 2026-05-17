"""Element template CRUD service (ADR-191, issue #153).

Templates capture a snapshot of selected fields from a source element
so later element creation can be pre-filled. Set-scoped by default;
``is_global`` promotes a template across sets. ``included_fields`` is
filtered against ``INCLUDED_FIELD_WHITELIST`` to keep the surface
narrow.

Row access is positional throughout (Protocol §15) so the same code
runs on SQLite and Supabase.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.element_templates.models import INCLUDED_FIELD_WHITELIST

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


class ElementTemplateScopeError(ValueError):
    """Raised when (set_id, is_global) are inconsistent.

    Router maps to HTTP 422. The DB CHECK constraint enforces the same
    invariant — this gives callers a clearer error than a generic
    constraint-violation 500.
    """


class ElementTemplateNotFoundError(LookupError):
    """Raised when a template can't be located (e.g. soft-deleted or
    missing). Router maps to 404.
    """


def _validate_scope(*, set_id: str | None, is_global: bool) -> None:
    """is_global=True ↔ set_id is None. Otherwise reject."""
    if is_global and set_id is not None:
        msg = "is_global templates must not have a set_id"
        raise ElementTemplateScopeError(msg)
    if not is_global and set_id is None:
        msg = "non-global templates require a set_id"
        raise ElementTemplateScopeError(msg)


def _filter_included_fields(fields: list[str]) -> list[str]:
    """Drop unknown fields silently, preserving caller-supplied order
    for the subset that survives."""
    seen: set[str] = set()
    out: list[str] = []
    for f in fields:
        if f in INCLUDED_FIELD_WHITELIST and f not in seen:
            out.append(f)
            seen.add(f)
    return out


async def _load_source_element(
    db: DatabasePort, element_id: str,
) -> dict[str, Any]:
    """Pull just the columns/JSON we may snapshot. Positional access."""
    cursor = await db.execute(
        "SELECT e.id, e.element_type, e.notation, ev.name, ev.description, "
        "ev.data, ev.metadata, e.package_id "
        "FROM elements e "
        "JOIN element_versions ev ON e.id = ev.element_id "
        "AND e.current_version = ev.version "
        "WHERE e.id = ? AND e.is_deleted = 0",
        (element_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        msg = f"Source element {element_id} not found"
        raise ElementTemplateNotFoundError(msg)
    src: dict[str, Any] = {
        "element_type": row[1],
        "notation": row[2] or "simple",
        "name": row[3],
        "description": row[4],
        "data": json.loads(row[5]) if row[5] else {},
        "metadata": json.loads(row[6]) if row[6] else None,
        "package_id": row[7],
    }
    # Pull tags positionally
    tag_cursor = await db.execute(
        "SELECT tag FROM element_tags WHERE element_id = ? ORDER BY tag",
        (element_id,),
    )
    tag_rows = await tag_cursor.fetchall()
    src["tags"] = [r[0] for r in tag_rows]
    return src


def _project_template_data(
    src: dict[str, Any], included_fields: list[str],
) -> dict[str, Any]:
    """Snapshot only the included fields from the source element."""
    return {k: src.get(k) for k in included_fields}


async def create_element_template(
    db: DatabasePort,
    *,
    source_element_id: str,
    name: str,
    description: str | None,
    included_fields: list[str],
    set_id: str | None,
    is_global: bool,
    created_by: str,
) -> dict[str, Any]:
    """Create a new template by snapshotting an element."""
    _validate_scope(set_id=set_id, is_global=is_global)
    filtered = _filter_included_fields(included_fields)
    if not filtered:
        msg = (
            "included_fields must contain at least one whitelisted "
            f"field. Whitelist: {sorted(INCLUDED_FIELD_WHITELIST)}"
        )
        raise ElementTemplateScopeError(msg)
    src = await _load_source_element(db, source_element_id)
    template_data = _project_template_data(src, filtered)
    template_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    # Literal ``, 0)`` for is_deleted caused HTTP 500 on Supabase —
    # PostgreSQL BOOLEAN columns reject integer literals (Protocol §15).
    # The adapter rewrites ``is_xxx = 0/1`` equality and retries int
    # params as booleans, but cannot rewrite a bare literal in VALUES.
    # Both schemas DEFAULT is_deleted to the correct false value, so
    # omit the column entirely and let the default apply.
    await db.execute(
        "INSERT INTO element_templates "
        "(id, name, description, set_id, is_global, source_element_id, "
        "included_fields, template_data, created_by, created_at, "
        "updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            template_id, name, description, set_id, 1 if is_global else 0,
            source_element_id, json.dumps(filtered),
            json.dumps(template_data), created_by, now, now,
        ),
    )
    await db.commit()
    return await get_element_template(db, template_id)  # type: ignore[return-value]


async def get_element_template(
    db: DatabasePort, template_id: str,
) -> dict[str, Any] | None:
    """Fetch a single template, enriched with denormalised names."""
    cursor = await db.execute(
        "SELECT t.id, t.name, t.description, t.set_id, s.name, "
        "t.is_global, t.source_element_id, "
        "(SELECT ev.name FROM element_versions ev "
        "  JOIN elements e ON e.id = ev.element_id "
        "  WHERE e.id = t.source_element_id "
        "  AND e.current_version = ev.version) AS source_name, "
        "t.included_fields, t.template_data, t.created_by, "
        "u.username, t.created_at, t.updated_at "
        "FROM element_templates t "
        "LEFT JOIN sets s ON s.id = t.set_id "
        "LEFT JOIN users u ON u.id = t.created_by "
        "WHERE t.id = ? AND t.is_deleted = 0",
        (template_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "name": row[1],
        "description": row[2],
        "set_id": row[3],
        "set_name": row[4],
        "is_global": bool(row[5]),
        "source_element_id": row[6],
        "source_element_name": row[7],
        "included_fields": json.loads(row[8]) if row[8] else [],
        "template_data": json.loads(row[9]) if row[9] else {},
        "created_by": row[10],
        "created_by_username": row[11] or "Unknown",
        "created_at": row[12],
        "updated_at": row[13],
    }


async def list_element_templates(
    db: DatabasePort,
    *,
    set_id: str | None = None,
    include_global: bool = True,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    """List templates. Returns (items, total).

    Scoping:
      - set_id=None, include_global=True → all globals only.
      - set_id="<uuid>", include_global=True → templates in that set
        plus all globals.
      - set_id="<uuid>", include_global=False → only that set.
    """
    where_parts = ["t.is_deleted = 0"]
    params: list[Any] = []
    if set_id is not None and include_global:
        where_parts.append("(t.set_id = ? OR t.is_global = 1)")
        params.append(set_id)
    elif set_id is not None:
        where_parts.append("t.set_id = ?")
        params.append(set_id)
    elif include_global:
        where_parts.append("t.is_global = 1")
    else:
        # set_id None and not include_global → empty result.
        return [], 0
    where_sql = " AND ".join(where_parts)

    count_cursor = await db.execute(
        f"SELECT COUNT(*) FROM element_templates t WHERE {where_sql}",
        tuple(params),
    )
    count_row = await count_cursor.fetchone()
    total: int = count_row[0] if count_row else 0

    offset = (page - 1) * page_size
    list_cursor = await db.execute(
        "SELECT t.id, t.name, t.description, t.set_id, s.name, "
        "t.is_global, t.source_element_id, "
        "(SELECT ev.name FROM element_versions ev "
        "  JOIN elements e ON e.id = ev.element_id "
        "  WHERE e.id = t.source_element_id "
        "  AND e.current_version = ev.version) AS source_name, "
        "t.included_fields, t.template_data, t.created_by, "
        "u.username, t.created_at, t.updated_at "
        "FROM element_templates t "
        "LEFT JOIN sets s ON s.id = t.set_id "
        "LEFT JOIN users u ON u.id = t.created_by "
        f"WHERE {where_sql} "
        "ORDER BY t.is_global DESC, t.name ASC "
        "LIMIT ? OFFSET ?",
        (*params, page_size, offset),
    )
    rows = await list_cursor.fetchall()
    items = [
        {
            "id": r[0],
            "name": r[1],
            "description": r[2],
            "set_id": r[3],
            "set_name": r[4],
            "is_global": bool(r[5]),
            "source_element_id": r[6],
            "source_element_name": r[7],
            "included_fields": json.loads(r[8]) if r[8] else [],
            "template_data": json.loads(r[9]) if r[9] else {},
            "created_by": r[10],
            "created_by_username": r[11] or "Unknown",
            "created_at": r[12],
            "updated_at": r[13],
        }
        for r in rows
    ]
    return items, total


async def update_element_template(
    db: DatabasePort,
    template_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    included_fields: list[str] | None = None,
    set_id: str | None | type[Ellipsis] = ...,  # ... = "not touched"
    is_global: bool | None = None,
) -> dict[str, Any] | None:
    """Edit a template's mutable fields.

    Re-projects ``template_data`` from the source element when
    ``included_fields`` changes AND the source element is still alive.
    If the source has been deleted, the existing ``template_data`` is
    filtered down to the intersection with the new ``included_fields``.
    """
    existing = await get_element_template(db, template_id)
    if existing is None:
        return None

    new_name = name if name is not None else existing["name"]
    new_description = (
        description if description is not None else existing["description"]
    )
    new_is_global = (
        is_global if is_global is not None else existing["is_global"]
    )
    new_set_id: str | None
    if set_id is ...:
        new_set_id = existing["set_id"]
    else:
        new_set_id = set_id  # may be None or a string
    _validate_scope(set_id=new_set_id, is_global=new_is_global)

    new_included = (
        _filter_included_fields(included_fields)
        if included_fields is not None
        else list(existing["included_fields"])
    )
    if not new_included:
        msg = "included_fields must contain at least one whitelisted field"
        raise ElementTemplateScopeError(msg)

    new_data = existing["template_data"]
    if included_fields is not None:
        # Re-project: prefer fresh data from the source element if it
        # still exists; otherwise keep the prior snapshot for fields
        # that survived the included_fields filter.
        try:
            src = await _load_source_element(
                db, existing["source_element_id"],
            ) if existing.get("source_element_id") else None
        except ElementTemplateNotFoundError:
            src = None
        if src is not None:
            new_data = _project_template_data(src, new_included)
        else:
            new_data = {k: existing["template_data"].get(k) for k in new_included}

    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "UPDATE element_templates SET "
        "name = ?, description = ?, set_id = ?, is_global = ?, "
        "included_fields = ?, template_data = ?, updated_at = ? "
        "WHERE id = ? AND is_deleted = 0",
        (
            new_name, new_description, new_set_id,
            1 if new_is_global else 0,
            json.dumps(new_included), json.dumps(new_data), now,
            template_id,
        ),
    )
    await db.commit()
    return await get_element_template(db, template_id)


async def delete_element_template(
    db: DatabasePort, template_id: str,
) -> bool:
    """Soft-delete a template. Returns True if a row was updated."""
    cursor = await db.execute(
        "UPDATE element_templates SET is_deleted = 1 "
        "WHERE id = ? AND is_deleted = 0",
        (template_id,),
    )
    await db.commit()
    return (cursor.rowcount or 0) > 0


def apply_template_to_create_body(
    template: dict[str, Any], request_body: dict[str, Any],
) -> dict[str, Any]:
    """Merge ``template.template_data`` under explicit request fields.

    Used by ``POST /api/elements`` when the caller supplies
    ``template_id``. Rules:
      - Only fields in ``template.included_fields`` are eligible.
      - Explicit request fields ALWAYS win (the user's typed values
        are not overwritten by template defaults).
      - Tags are merged separately by the caller via the tags table —
        we just pass the list through.
    """
    merged = dict(request_body)
    data: dict[str, Any] = template.get("template_data") or {}
    for key in template.get("included_fields") or []:
        if key in merged and merged[key] is not None:
            continue
        if key in data:
            merged[key] = data[key]
    return merged
