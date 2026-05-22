"""Element template CRUD service (ADR-191, issue #153; ADR-211, v6.19.0).

Templates carry reusable element content: either a snapshot of an
existing element (ADR-191) or direct content with an optional
``markdown_stamp`` (ADR-211). Set-scoped by default; ``is_global``
promotes a template across sets. ``included_fields`` is filtered
against ``INCLUDED_FIELD_WHITELIST`` to keep the surface narrow.

Row access is positional throughout (Protocol §15) so the same code
runs on SQLite and Supabase.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.element_templates.models import INCLUDED_FIELD_WHITELIST

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


# ADR-211: `{{self:<field-spec>}}` placeholder used in markdown_stamp.
_SELF_TOKEN_RE = re.compile(r"\{\{self:([^}]+)\}\}")

# ADR-215 (v6.27.0): regex that extracts attribute NAMEs from
# self:attr:attributes/<NAME>/<rest> tokens in a stamp body. The
# stamp's required-attribute set drives whether it applies to a
# given element via SPEC-211-d's body-parsing filter.
_BODY_ATTR_TOKEN_RE = re.compile(
    r"\{\{self:attr:attributes/([^/}]+)/[^}]+\}\}",
)


def substitute_self(stamp_body: str, element_id: str) -> str:
    """Rewrite ``{{self:<field-spec>}}`` → ``{{element:<element_id>:<field-spec>}}``.

    Used at picker insert time so the resulting body is a normal smart-
    markdown fragment with concrete element IDs. ADR-211.
    """
    return _SELF_TOKEN_RE.sub(
        lambda m: f"{{{{element:{element_id}:{m.group(1)}}}}}",
        stamp_body,
    )


def _required_attr_names(stamp_body: str | None) -> set[str]:
    """ADR-215: return the set of attribute NAMEs referenced by
    ``{{self:attr:attributes/<NAME>/<rest>}}`` tokens in the stamp body.

    Empty result means the body uses no attribute references — the
    body filter is trivially satisfied for any element."""
    if not stamp_body:
        return set()
    return set(_BODY_ATTR_TOKEN_RE.findall(stamp_body))


def _element_attr_names(element_data: dict[str, Any]) -> set[str]:
    """Return the set of attribute names on element.data.attributes."""
    attrs = element_data.get("attributes")
    if not isinstance(attrs, list):
        return set()
    out: set[str] = set()
    for a in attrs:
        if isinstance(a, dict):
            name = a.get("name")
            if isinstance(name, str):
                out.add(name)
    return out


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
    source_element_id: str | None,
    name: str,
    description: str | None,
    included_fields: list[str],
    set_id: str | None,
    is_global: bool,
    created_by: str,
    template_data_direct: dict[str, Any] | None = None,
    markdown_stamp: str | None = None,
) -> dict[str, Any]:
    """Create a new template (ADR-191 + ADR-211).

    Three content paths:
      1. ``source_element_id`` + ``included_fields`` → snapshot from element.
      2. ``template_data_direct`` (non-empty) → use as-is.
      3. ``markdown_stamp`` only → stamp-only template.

    At least one path must yield non-empty content.
    """
    _validate_scope(set_id=set_id, is_global=is_global)

    filtered = _filter_included_fields(included_fields)
    template_data: dict[str, Any] = {}

    if source_element_id is not None:
        src = await _load_source_element(db, source_element_id)
        if filtered:
            template_data = _project_template_data(src, filtered)
    elif template_data_direct is not None:
        template_data = dict(template_data_direct)

    has_data = bool(template_data)
    has_stamp = bool(markdown_stamp and markdown_stamp.strip())

    if not has_data and not has_stamp:
        msg = (
            "Template must have at least one of: a source_element_id "
            "with included_fields, template_data, or markdown_stamp."
        )
        raise ElementTemplateScopeError(msg)

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
        "included_fields, template_data, markdown_stamp, created_by, "
        "created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            template_id, name, description, set_id, 1 if is_global else 0,
            source_element_id, json.dumps(filtered),
            json.dumps(template_data),
            markdown_stamp if has_stamp else None,
            created_by, now, now,
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
        "  AND e.current_version = ev.version "
        "  AND e.is_deleted = 0) AS source_name, "
        "t.included_fields, t.template_data, t.created_by, "
        "u.username, t.created_at, t.updated_at, t.markdown_stamp "
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
        "markdown_stamp": row[14],
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
        "  AND e.current_version = ev.version "
        "  AND e.is_deleted = 0) AS source_name, "
        "t.included_fields, t.template_data, t.created_by, "
        "u.username, t.created_at, t.updated_at, t.markdown_stamp "
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
            "markdown_stamp": r[14],
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
    template_data_direct: dict[str, Any] | None | type[Ellipsis] = ...,
    markdown_stamp: str | None | type[Ellipsis] = ...,
) -> dict[str, Any] | None:
    """Edit a template's mutable fields.

    Re-projects ``template_data`` from the source element when
    ``included_fields`` changes AND the source element is still alive.
    If the source has been deleted, the existing ``template_data`` is
    filtered down to the intersection with the new ``included_fields``.

    ADR-211: ``markdown_stamp`` and ``template_data_direct`` are
    sentinel-or-value parameters (``...`` means "not touched"). Setting
    ``markdown_stamp`` to ``None`` clears it.
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

    # included_fields: optional. ADR-211 relaxes the prior "must be
    # non-empty" rule — a stamp-only template can carry an empty list.
    new_included: list[str]
    if included_fields is not None:
        new_included = _filter_included_fields(included_fields)
    else:
        new_included = list(existing["included_fields"])

    # template_data:
    #   - If the caller passed template_data_direct (sentinel not Ellipsis),
    #     use that directly (write-through).
    #   - Else if included_fields was reshaped, re-project from source.
    #   - Else carry forward existing.
    new_data: dict[str, Any]
    if template_data_direct is not ...:
        new_data = dict(template_data_direct) if template_data_direct else {}
    elif included_fields is not None and new_included:
        try:
            src = await _load_source_element(
                db, existing["source_element_id"],
            ) if existing.get("source_element_id") else None
        except ElementTemplateNotFoundError:
            src = None
        if src is not None:
            new_data = _project_template_data(src, new_included)
        else:
            new_data = {
                k: existing["template_data"].get(k) for k in new_included
            }
    else:
        new_data = existing["template_data"]

    # markdown_stamp: ... = no change; None = clear; str = set.
    new_stamp: str | None
    if markdown_stamp is ...:
        new_stamp = existing.get("markdown_stamp")
    else:
        new_stamp = markdown_stamp

    # Validation: template still must have at least one of data/stamp/included
    if not new_data and not (new_stamp and new_stamp.strip()) and not new_included:
        msg = (
            "Template must keep at least one of: included_fields, "
            "template_data, or markdown_stamp"
        )
        raise ElementTemplateScopeError(msg)

    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "UPDATE element_templates SET "
        "name = ?, description = ?, set_id = ?, is_global = ?, "
        "included_fields = ?, template_data = ?, markdown_stamp = ?, "
        "updated_at = ? "
        "WHERE id = ? AND is_deleted = 0",
        (
            new_name, new_description, new_set_id,
            1 if new_is_global else 0,
            json.dumps(new_included), json.dumps(new_data), new_stamp,
            now,
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


async def list_stamps_for_element(
    db: DatabasePort, element_id: str,
) -> list[dict[str, Any]]:
    """Return in-scope stamps for an element.

    Filter rules:

    1. Scope (ADR-211): the template is global (``is_global = 1``) OR
       set-scoped to the element's set.
    2. Element type (ADR-211): the template's captured ``element_type``
       matches the element's ``element_type`` (or the template doesn't
       capture an element_type — then it's offered for any).
    3. Body attributes (ADR-215): every attribute name referenced by
       the stamp body via ``{{self:attr:attributes/<NAME>/<rest>}}``
       must be present on the element's ``data.attributes``. Stamps
       whose body uses no ``attr:`` references pass trivially.

    Each returned ``markdown_stamp`` has ``{{self:…}}`` already
    substituted with the element's ID so the picker can paste it
    directly.
    """
    # Resolve element's set_id + element_type + data.
    cursor = await db.execute(
        "SELECT e.set_id, e.element_type, ev.data "
        "FROM elements e "
        "JOIN element_versions ev ON e.id = ev.element_id "
        "  AND e.current_version = ev.version "
        "WHERE e.id = ? AND e.is_deleted = 0",
        (element_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return []
    set_id, element_type = row[0], row[1]
    raw_data = row[2]
    try:
        element_data: dict[str, Any] = (
            json.loads(raw_data) if isinstance(raw_data, str) else (raw_data or {})
        )
    except (json.JSONDecodeError, TypeError):
        element_data = {}
    if not isinstance(element_data, dict):
        element_data = {}
    elem_attr_names = _element_attr_names(element_data)

    cursor = await db.execute(
        "SELECT id, name, description, set_id, is_global, "
        "template_data, markdown_stamp "
        "FROM element_templates "
        "WHERE is_deleted = 0 "
        "AND markdown_stamp IS NOT NULL AND markdown_stamp != '' "
        "AND (is_global = 1 OR set_id = ?) "
        "ORDER BY is_global DESC, name ASC",
        (set_id,),
    )
    rows = await cursor.fetchall()

    out: list[dict[str, Any]] = []
    for r in rows:
        td = json.loads(r[5]) if r[5] else {}
        td_etype = td.get("element_type") if isinstance(td, dict) else None
        if td_etype and td_etype != element_type:
            continue
        stamp_body = r[6] or ""
        # ADR-215 body-parsing filter: every attribute name referenced
        # by the stamp body must exist on the element.
        required = _required_attr_names(stamp_body)
        if required and not required.issubset(elem_attr_names):
            continue
        resolved = substitute_self(stamp_body, element_id)
        out.append({
            "id": r[0],
            "name": r[1],
            "description": r[2],
            "set_id": r[3],
            "is_global": bool(r[4]),
            "markdown_stamp": resolved,
        })
    return out
