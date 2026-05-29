"""Compute module for the smart_markdown diagram type (ADR-205, issue #185).

Resolves inline-reference tokens in user-edited markdown source against
live Iris entity fields. The user writes markdown with tokens of the form

    {{<entity-type>:<id>:<field-spec>}}

where ``entity-type`` is one of ``element``, ``package``, ``diagram``,
``set``, ``collection``; ``id`` is the entity's GUID; and ``field-spec``
is ``name``, ``description``, or (for elements only) ``attr:<key>``
where ``<key>`` is a key in the element's ``data`` JSON.

ADR-210 (v6.18.0): ``<field-spec>`` may carry an inline ``=<value>``
override — ``{{element:UUID:attr:Quantity=500}}`` resolves to "500"
regardless of the stored value. An empty override (``...path=``) is the
"fillable slot" marker — render as strikethrough so the unfilled slot
is visible. Splits on the first ``=`` only, so override values may
contain ``=``. Dangling entity references still strike through even
when an override is present.

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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


_PLACEHOLDER = "_No content yet._"

# entity-type, id, field-spec. ID rejects ``:`` and ``}`` so multi-segment
# field-specs (``attr:<key>``) bind to the third group only.
# ADR-209 (v6.17.0): `image` is a new entity-type variant. Image tokens
# may omit the field-spec entirely (`{{image:<id>}}` for original size)
# or carry a sizing directive (`width:50%`, `width:300px`, `height:N%`,
# `height:Npx`, or `original`). Making the third segment optional is
# safe because non-image entity types validate field-spec separately in
# `_resolve_one` (missing/invalid → strikethrough).
_TOKEN_RE = re.compile(
    r"\{\{(element|package|diagram|set|collection|image):"
    r"([^:}]+)"
    r"(?::([^}]*))?"
    r"\}\}"
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


def _resolve_attr_path(node: Any, segments: list[str]) -> Any | None:
    """Walk ``node`` along ``segments``. Returns the resolved value, or None.

    Per ADR-206:
    - dict node + segment matching a key → take ``node[seg]``.
    - list node + numeric segment → index into the list.
    - list node + non-numeric segment where every item is a dict
      with a ``name`` field → find first item where ``item['name']``
      equals the segment.
    - primitive node with more segments remaining → unresolvable.

    Numeric segments always index even when items happen to have
    ``name`` fields (explicit index wins).
    """
    for seg in segments:
        if isinstance(node, dict):
            if seg in node:
                node = node[seg]
                continue
            return None
        if isinstance(node, list):
            if seg.isdigit():
                idx = int(seg)
                if 0 <= idx < len(node):
                    node = node[idx]
                    continue
                return None
            if node and all(
                isinstance(item, dict) and "name" in item for item in node
            ):
                match = next(
                    (item for item in node if item.get("name") == seg), None,
                )
                if match is None:
                    return None
                node = match
                continue
            return None
        # primitive but more segments remain
        return None
    return node


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
        raw_path = field_spec[len("attr:"):]
        segments = [s for s in raw_path.split("/") if s]
        if not segments:
            return None
        raw = row[2]
        if raw is None:
            return None
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            return None
        if not isinstance(data, dict):
            return None
        resolved = _resolve_attr_path(data, segments)
        if resolved is None:
            return None
        # Legacy v6.14.x: single-segment tokens that landed on a dict
        # or list rendered the JSON literal. Preserve that — new
        # tokens with a multi-segment path simply drill further.
        if isinstance(resolved, (dict, list)):
            return str(resolved)
        return str(resolved)
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


_IMAGE_SIZING_RE = re.compile(r"^(width|height):(\d{1,4})(%|px)$")


def _format_image_style(sizing: str | None) -> str:
    """Return the inline CSS for an image sizing directive (ADR-209).

    Accepts: ``None`` / "" / "original" → no style.
             "width:N%" / "width:Npx"   → ``style="width:N%"``.
             "height:N%" / "height:Npx" → ``style="height:N%"``.

    Anything else → empty (render at original size; the token isn't
    flagged as unresolvable since the image itself is valid).
    """
    if not sizing or sizing == "original":
        return ""
    m = _IMAGE_SIZING_RE.fullmatch(sizing.strip())
    if not m:
        return ""
    axis, num, unit = m.group(1), m.group(2), m.group(3)
    return f'style="{axis}:{num}{unit}"'


async def _resolve_image(
    db: DatabasePort, image_id: str, sizing: str | None,
) -> str | None:
    """Resolve an image token to an ``<img>`` tag (ADR-209)."""
    cursor = await db.execute(
        "SELECT 1 FROM images WHERE id = ?", (image_id,),
    )
    if (await cursor.fetchone()) is None:
        return None  # → strikethrough fallback
    style_attr = _format_image_style(sizing)
    if style_attr:
        return f'<img src="/api/images/{image_id}" {style_attr} alt="">'
    return f'<img src="/api/images/{image_id}" alt="">'


async def _fetch_entity_display_name(
    db: DatabasePort, entity_type: str, entity_id: str,
) -> str | None:
    """Fetch the display name for an entity (ADR-209, v6.17.0).

    Used to populate the tooltip on the markdown link that wraps a
    resolved entity-field value, so hovering shows the entity name
    even when the resolved value is e.g. an attribute string like "g".
    """
    if entity_type == "element":
        cursor = await db.execute(
            "SELECT ev.name FROM elements e "
            "JOIN element_versions ev ON e.id = ev.element_id "
            "  AND e.current_version = ev.version "
            "WHERE e.id = ? AND e.is_deleted = 0",
            (entity_id,),
        )
    elif entity_type == "package":
        cursor = await db.execute(
            "SELECT pv.name FROM packages p "
            "JOIN package_versions pv ON p.id = pv.package_id "
            "  AND p.current_version = pv.version "
            "WHERE p.id = ? AND p.is_deleted = 0",
            (entity_id,),
        )
    elif entity_type == "diagram":
        cursor = await db.execute(
            "SELECT dv.name FROM diagrams d "
            "JOIN diagram_versions dv ON d.id = dv.diagram_id "
            "  AND d.current_version = dv.version "
            "WHERE d.id = ? AND d.is_deleted = 0",
            (entity_id,),
        )
    elif entity_type == "set":
        cursor = await db.execute(
            "SELECT name FROM sets WHERE id = ? AND is_deleted = 0",
            (entity_id,),
        )
    elif entity_type == "collection":
        cursor = await db.execute(
            "SELECT name FROM collections WHERE id = ?", (entity_id,),
        )
    else:
        return None
    row = await cursor.fetchone()
    return row[0] if row else None


def _markdown_escape_link_text(value: str) -> str:
    """Escape characters in a string so it's safe as the *text* of a
    markdown link `[text](url)`. Square brackets break the link
    syntax; backslash-escape them. Other chars are fine."""
    return value.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def _markdown_escape_title(value: str) -> str:
    """Escape characters in a markdown link title `"<title>"`."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


async def _resolve_element_detail_diagram(
    db: DatabasePort, element_id: str,
) -> str | None:
    """Resolve ``{{element:<id>:detail_diagram}}`` (ADR-221).

    Unlike other element tokens — which link back to the element — this
    resolves to a link to the element's *detail diagram* so the rendered
    markdown drills into the diagram that elaborates the element. Returns
    ``None`` (→ strikethrough) when the element has no detail diagram, or
    the target diagram is missing/soft-deleted.
    """
    cursor = await db.execute(
        "SELECT detail_diagram_id FROM elements "
        "WHERE id = ? AND is_deleted = 0",
        (element_id,),
    )
    row = await cursor.fetchone()
    if not row or not row[0]:
        return None
    detail_id = row[0]
    name = await _fetch_entity_display_name(db, "diagram", detail_id)
    if name is None:
        return None
    title = _markdown_escape_title(name)
    text = _markdown_escape_link_text(name)
    return f'[{text}](iris://diagram/{detail_id} "{title}")'


async def _resolve_one(
    db: DatabasePort, entity_type: str, entity_id: str, field_spec: str | None,
) -> str | None:
    """Return the resolved value, or None if unresolvable.

    None signals: entity missing / deleted, field invalid for the type,
    attribute key missing, or empty-override fillable-slot marker.
    Callers turn None into strikethrough.

    ADR-209 (v6.17.0): entity-reference values are wrapped in a markdown
    link `[value](iris://<type>/<id> "<entity name>")` so MarkdownView
    routes the click and shows the name as a hover tooltip. Images
    (`{{image:...}}`) are returned as raw `<img>` HTML and are NOT
    wrapped.

    ADR-210 (v6.18.0): if ``field_spec`` contains ``=``, split on the
    first one — the suffix is an inline override value used in place
    of the stored field. Empty override (``...path=``) → return None so
    the token renders as strikethrough (the "fillable slot" marker).
    Dangling entity references still strike through regardless of
    override.
    """
    if entity_type == "image":
        return await _resolve_image(db, entity_id, field_spec)
    # Non-image entity types require a field_spec.
    if field_spec is None or field_spec == "":
        return None

    # ADR-221: an element's detail-diagram drill. Resolves to a link to
    # the *target diagram*, not the element — so it's handled before the
    # generic element-field path (which would wrap in an element link).
    if entity_type == "element" and field_spec == "detail_diagram":
        return await _resolve_element_detail_diagram(db, entity_id)

    # ADR-210: parse inline =value override.
    field_spec_path: str = field_spec
    override_value: str | None = None
    if "=" in field_spec:
        field_spec_path, override_value = field_spec.split("=", 1)
        if override_value == "":
            # Fillable-slot marker — author declared "fill this in,"
            # leave unfilled → strikethrough (don't fall through to
            # stored value).
            return None

    raw_value: str | None
    if override_value is not None:
        raw_value = override_value
    elif entity_type == "element":
        raw_value = await _fetch_element_field(db, entity_id, field_spec_path)
    elif entity_type == "package":
        raw_value = await _fetch_named_field(
            db, table="packages", versions_table="package_versions",
            fk="package_id", entity_id=entity_id, field_spec=field_spec_path,
        )
    elif entity_type == "diagram":
        raw_value = await _fetch_named_field(
            db, table="diagrams", versions_table="diagram_versions",
            fk="diagram_id", entity_id=entity_id, field_spec=field_spec_path,
        )
    elif entity_type == "set":
        raw_value = await _fetch_set_field(db, entity_id, field_spec_path)
    elif entity_type == "collection":
        raw_value = await _fetch_collection_field(db, entity_id, field_spec_path)
    else:
        return None

    if raw_value is None:
        return None

    # Wrap in an iris:// markdown link so the rendered output is a
    # clickable, tooltip-bearing reference to the source entity.
    # ADR-210: even with an override, look up the entity to confirm it
    # exists — a dangling reference should strike through regardless.
    name = await _fetch_entity_display_name(db, entity_type, entity_id)
    if name is None:
        return None
    title = _markdown_escape_title(name)
    text = _markdown_escape_link_text(str(raw_value))
    return f'[{text}](iris://{entity_type}/{entity_id} "{title}")'


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
