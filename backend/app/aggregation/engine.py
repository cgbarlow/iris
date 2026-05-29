"""Generic aggregation engine (ADR-212, SPEC-212-b).

One function — ``run(db, profile_id, source_diagram_id)`` — walks the
source diagram (and, optionally, sub-diagrams it references) for
tokens of a configured type, resolves attribute values (using ADR-210
``=value`` overrides as the primary value source), groups by
``(token_id, bucket)``, aggregates, groups again by an output
``group_by`` attribute, formats each line with a configurable template,
and returns a markdown string.

The engine is parameterised entirely by data (the profile JSON). No
domain terminology lives in this module.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.aggregation.exceptions import (
    AggregationProfileNotFound,
    AggregationSourceNotFound,
)
from app.aggregation.models import (
    AggregationResult,
    OuterStep,
    OutputConfig,
    ProfileData,
    TraversalConfig,
)
from app.aggregation.profiles_service import get_aggregation_profile
from app.diagrams.smart_markdown import (  # DRY §13
    _TOKEN_RE,
    _extract_tagged_value,
    _fetch_element_diagram_usage_count,
    _fetch_element_relationship_count,
    _parse_metadata,
)

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


# ─────────────────────────────────────────────────────────────────────
# Internal dataclasses
# ─────────────────────────────────────────────────────────────────────


@dataclass
class _ParsedToken:
    entity_type: str
    entity_id: str
    field_spec: str | None
    field_spec_path: str | None  # field_spec with `=value` stripped
    override_value: str | None   # the part after the first `=`, or None

    def override_for(self, path: str) -> str | None:
        """Return the override value IFF this token's field_spec_path
        equals the requested path."""
        if self.override_value is None or self.field_spec_path is None:
            return None
        # The path may be a bare path like "attributes/Q/type" or have
        # an "attr:" prefix when used as a field_spec. Compare both
        # forms.
        if self.field_spec_path == path:
            return self.override_value
        if self.field_spec_path == f"attr:{path}":
            return self.override_value
        return None


@dataclass
class _Row:
    token_id: str           # entity id from the inner token
    bucket: str             # bucket value (empty string when no bucket)
    scaled_value: float
    source_label: str       # outer-source diagram name (or self if no outer)


@dataclass
class _GroupedRow:
    token_id: str
    bucket: str
    value: float
    sources: list[tuple[str, float]] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _parse_tokens(
    markdown: str, token_type: str,
) -> list[_ParsedToken]:
    """Iterate smart_markdown tokens of the given type. Splits the
    field_spec on the first `=` per ADR-210."""
    out: list[_ParsedToken] = []
    for m in _TOKEN_RE.finditer(markdown):
        etype = m.group(1)
        if etype != token_type:
            continue
        eid = m.group(2)
        spec = m.group(3)
        path: str | None = spec
        override: str | None = None
        if spec is not None and "=" in spec:
            path, override = spec.split("=", 1)
        out.append(_ParsedToken(
            entity_type=etype, entity_id=eid,
            field_spec=spec,
            field_spec_path=path,
            override_value=override,
        ))
    return out


async def _read_smart_markdown_source(
    db: DatabasePort, diagram_id: str,
) -> str:
    """Return the diagram's data.markdown_source, or '' if absent."""
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


async def _read_diagram_data(
    db: DatabasePort, diagram_id: str,
) -> dict[str, Any]:
    """Return the diagram's data JSON, or {}."""
    cursor = await db.execute(
        "SELECT dv.data FROM diagrams d "
        "JOIN diagram_versions dv ON d.id = dv.diagram_id "
        "  AND d.current_version = dv.version "
        "WHERE d.id = ? AND d.is_deleted = 0",
        (diagram_id,),
    )
    row = await cursor.fetchone()
    if not row or not row[0]:
        return {}
    try:
        data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
    except (json.JSONDecodeError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


async def _diagram_meta(
    db: DatabasePort, diagram_id: str,
) -> tuple[str | None, int | None]:
    """Return (name, current_version) for a diagram, or (None, None)."""
    cursor = await db.execute(
        "SELECT dv.name, d.current_version "
        "FROM diagrams d "
        "JOIN diagram_versions dv ON d.id = dv.diagram_id "
        "  AND d.current_version = dv.version "
        "WHERE d.id = ? AND d.is_deleted = 0",
        (diagram_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None, None
    return row[0], row[1]


async def _read_element_data(
    db: DatabasePort, element_id: str,
) -> tuple[str | None, str | None, dict[str, Any]]:
    """Return (name, package_name, data) for an element. (None, None, {})
    if missing/deleted."""
    cursor = await db.execute(
        "SELECT ev.name, ev.data, p.id, "
        "(SELECT pv.name FROM package_versions pv "
        "  JOIN packages pkg ON pkg.id = pv.package_id "
        "  WHERE pkg.id = e.package_id "
        "    AND pkg.current_version = pv.version "
        "    AND pkg.is_deleted = 0) AS pkg_name "
        "FROM elements e "
        "JOIN element_versions ev ON e.id = ev.element_id "
        "  AND e.current_version = ev.version "
        "LEFT JOIN packages p ON p.id = e.package_id "
        "WHERE e.id = ? AND e.is_deleted = 0",
        (element_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None, None, {}
    try:
        data = json.loads(row[1]) if row[1] else {}
    except (json.JSONDecodeError, TypeError):
        data = {}
    return row[0], row[3], data if isinstance(data, dict) else {}


def _walk_attr_path(node: Any, path: str | None) -> Any:
    """Walk a slash-separated attribute path through dicts and lists
    (using the same semantics as smart_markdown ADR-206)."""
    if not path:
        return None
    segments = [s for s in path.split("/") if s]
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
                    (item for item in node if item.get("name") == seg),
                    None,
                )
                if match is None:
                    return None
                node = match
                continue
            return None
        return None
    return node


def _walk_diagram_data_path(data: dict[str, Any], path: str) -> Any:
    """Resolve `data.<field>` or `<field>` against the diagram data."""
    if path.startswith("data."):
        path = path[5:]
    return _walk_attr_path(data, path)


async def _resolve_token_value(
    db: DatabasePort,
    token: _ParsedToken,
    attribute_path: str | None,
) -> Any:
    """Return the token's value at attribute_path.

    Order:
      1. If the token carries a `=value` override on this exact path,
         the override wins.
      2. Otherwise look up the entity's stored attribute at the path.
    """
    if attribute_path is None:
        return None
    override = token.override_for(attribute_path)
    if override is not None:
        return override
    # Stored lookup — currently only elements have rich attribute
    # paths; for other entity types the path doesn't resolve and we
    # return None.
    if token.entity_type == "element":
        eid = token.entity_id
        # ADR-223: computed counts + metadata + EA tagged values, exposed
        # to aggregation profiles via well-known paths.
        if attribute_path == "relationship_count":
            return await _fetch_element_relationship_count(db, eid)
        if attribute_path == "diagram_usage_count":
            return await _fetch_element_diagram_usage_count(db, eid)
        if attribute_path.startswith("meta/"):
            key = attribute_path[len("meta/"):]
            meta = await _fetch_element_metadata_dict(db, eid)
            v = meta.get(key)
            if v is None:
                return None
            s = str(v).strip()
            return s or None
        if attribute_path.startswith("tag/"):
            prop = attribute_path[len("tag/"):]
            meta = await _fetch_element_metadata_dict(db, eid)
            return _extract_tagged_value(meta, prop)
        _, _, data = await _read_element_data(db, eid)
        return _walk_attr_path(data, attribute_path)
    return None


async def _fetch_element_metadata_dict(
    db: DatabasePort, element_id: str,
) -> dict[str, Any]:
    """Read the current-version metadata of an element (ADR-223)."""
    cursor = await db.execute(
        "SELECT ev.metadata FROM elements e "
        "JOIN element_versions ev ON e.id = ev.element_id "
        "  AND e.current_version = ev.version "
        "WHERE e.id = ? AND e.is_deleted = 0",
        (element_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return {}
    return _parse_metadata(row[0])


async def _resolve_multiplier(
    db: DatabasePort,
    outer_token: _ParsedToken,
    ref_diagram_id: str,
    outer: OuterStep,
) -> float:
    """Resolve the per-outer-token scaling multiplier.

    Semantics: the multiplier is *override / divisor* when the outer
    token carries a per-use override (the recipe-style "diners ÷
    servings" case). When there is no override, the multiplier is
    just ``default_multiplier`` — the divisor is NOT applied, because
    the absence of an override means "use this reference as-is."
    """
    rule = outer.multiplier
    if rule is None:
        return 1.0
    override_raw: str | None = None
    if rule.from_attribute_override:
        override_raw = outer_token.override_for(rule.from_attribute_override)
    if override_raw is None:
        # No per-use override → no scaling, just default.
        return float(rule.default_multiplier)
    try:
        numerator = float(override_raw)
    except (TypeError, ValueError):
        return float(rule.default_multiplier)
    divisor = 1.0
    if rule.divisor_from_diagram_data:
        data = await _read_diagram_data(db, ref_diagram_id)
        raw = _walk_diagram_data_path(data, rule.divisor_from_diagram_data)
        try:
            divisor = float(raw) if raw is not None else 1.0
        except (TypeError, ValueError):
            divisor = 1.0
    if divisor == 0:
        divisor = 1.0
    return numerator / divisor


async def _collect_inner(
    db: DatabasePort,
    markdown: str,
    inner: Any,  # InnerStep
    multiplier: float,
    source_label: str,
    accumulator: list[_Row],
    warnings: list[str],
) -> None:
    for tok in _parse_tokens(markdown, inner.collect_token_type):
        raw_value = await _resolve_token_value(
            db, tok, inner.value_attribute_path,
        )
        if raw_value is None or raw_value == "":
            if inner.skip_blank_values:
                continue
            scaled = 0.0
        else:
            try:
                scaled = float(raw_value) * multiplier
            except (TypeError, ValueError):
                warnings.append(
                    f"Non-numeric value '{raw_value}' on token "
                    f"{tok.entity_type}:{tok.entity_id} — counted as 0.",
                )
                scaled = 0.0
        bucket_raw = await _resolve_token_value(
            db, tok, inner.bucket_attribute_path,
        ) if inner.bucket_attribute_path else None
        bucket = "" if bucket_raw is None else str(bucket_raw)
        accumulator.append(_Row(
            token_id=tok.entity_id,
            bucket=bucket,
            scaled_value=scaled,
            source_label=source_label,
        ))


def _group_and_aggregate(
    rows: list[_Row], fn: str,
) -> list[_GroupedRow]:
    grouped: dict[tuple[str, str], list[_Row]] = defaultdict(list)
    for r in rows:
        grouped[(r.token_id, r.bucket)].append(r)
    out: list[_GroupedRow] = []
    for (token_id, bucket), items in grouped.items():
        if fn == "count":
            value: float = float(len(items))
        else:  # sum (default)
            value = sum(i.scaled_value for i in items)
        # Per-source breakdown: join entries from the same source label.
        per_source: dict[str, float] = defaultdict(float)
        for it in items:
            per_source[it.source_label] += it.scaled_value
        out.append(_GroupedRow(
            token_id=token_id, bucket=bucket, value=value,
            sources=sorted(per_source.items()),
        ))
    return out


# ─────────────────────────────────────────────────────────────────────
# Output formatting
# ─────────────────────────────────────────────────────────────────────


_GROUP_BY_RE = re.compile(r"^element\.(?P<rest>.+)$")


async def _resolve_group_value(
    db: DatabasePort,
    token_id: str,
    group_by: str | None,
    element_cache: dict[str, tuple[str | None, str | None, dict[str, Any]]],
) -> str:
    """Resolve a group_by expression against the (cached) element data."""
    if not group_by:
        return ""
    if token_id not in element_cache:
        element_cache[token_id] = await _read_element_data(db, token_id)
    name, pkg_name, data = element_cache[token_id]
    m = _GROUP_BY_RE.match(group_by)
    if not m:
        return ""
    rest = m.group("rest")
    # Special-cases
    if rest == "name":
        return name or ""
    if rest == "package_name":
        return pkg_name or ""
    # element.attributes.<path...> → walk element.data along path
    if rest.startswith("attributes."):
        sub = rest[len("attributes."):]
        # Convert dotted path to the slash convention used elsewhere.
        # E.g. "Author/type" → ["Author", "type"]; "attributes.Author.type" → ["Author", "type"]
        value = _walk_attr_path({"attributes": data.get("attributes")}, "attributes/" + sub)
        if value is None:
            return ""
        return str(value)
    # ADR-223: group by metadata, tagged values, or computed counts.
    if rest == "relationship_count":
        return str(await _fetch_element_relationship_count(db, token_id))
    if rest == "diagram_usage_count":
        return str(await _fetch_element_diagram_usage_count(db, token_id))
    if rest.startswith("meta."):
        key = rest[len("meta."):]
        meta = await _fetch_element_metadata_dict(db, token_id)
        v = meta.get(key)
        return "" if v is None else str(v).strip()
    if rest.startswith("tag."):
        prop = rest[len("tag."):]
        meta = await _fetch_element_metadata_dict(db, token_id)
        v = _extract_tagged_value(meta, prop)
        return v or ""
    return ""


def _fmt_value(v: float) -> str:
    """Render numeric value as int when it's a whole number."""
    if v == int(v):
        return str(int(v))
    # Strip insignificant trailing zeros for tidiness.
    return f"{v:g}"


def _substitute_placeholders(template: str, values: dict[str, str]) -> str:
    """Replace `{placeholder}` markers literally — supports dotted keys
    like `{element.name}` that Python's str.format can't handle as a
    bare kwarg.

    Unknown placeholders are left as-is rather than raising; the
    template is user-authored config, not code.
    """
    # Order longest first so e.g. {bucket_spaced} substitutes before
    # {bucket} (which would otherwise eat the prefix).
    for key in sorted(values.keys(), key=len, reverse=True):
        template = template.replace("{" + key + "}", values[key])
    return template


def _render_line(
    line_format: str,
    *,
    element_name: str,
    element_id: str,
    sum_value: float,
    bucket: str,
) -> str:
    return _substitute_placeholders(line_format, {
        "element.name": element_name,
        "element.id": element_id,
        "sum_value": _fmt_value(sum_value),
        "bucket": bucket,
        "bucket_spaced": f" {bucket}" if bucket else "",
    })


def _render_breakdown(
    breakdown_format: str,
    sources: list[tuple[str, float]],
) -> str:
    if not sources:
        return ""
    joined = ", ".join(
        f"{src} {_fmt_value(val)}" for src, val in sources
    )
    return _substitute_placeholders(breakdown_format, {
        "sources_joined": joined,
    })


async def _format_output(
    db: DatabasePort,
    grouped: list[_GroupedRow],
    output: OutputConfig,
) -> tuple[str, int]:
    """Group output by output.group_by, sort, format. Returns
    (markdown, row_count)."""
    element_cache: dict[str, tuple[str | None, str | None, dict[str, Any]]] = {}

    # Resolve display data for every token.
    rows_with_display: list[
        tuple[_GroupedRow, str, str]  # row, group_value, element_name
    ] = []
    for r in grouped:
        if r.token_id not in element_cache:
            element_cache[r.token_id] = await _read_element_data(db, r.token_id)
        name, _, _ = element_cache[r.token_id]
        element_name = name or "(missing)"
        group_value = await _resolve_group_value(
            db, r.token_id, output.group_by, element_cache,
        )
        rows_with_display.append((r, group_value or "(no group)", element_name))

    # Group output by group_value.
    groups: dict[str, list[tuple[_GroupedRow, str]]] = defaultdict(list)
    for r, gv, name in rows_with_display:
        groups[gv].append((r, name))

    # Sort groups.
    if output.sort_groups == "alpha":
        sorted_group_keys = sorted(groups.keys(), key=lambda s: s.lower())
    else:
        sorted_group_keys = list(groups.keys())

    out_lines: list[str] = []
    row_count = 0
    for group_key in sorted_group_keys:
        if output.group_by:
            out_lines.append(f"## {group_key}")
            out_lines.append("")
        # Sort items within group.
        items = groups[group_key]
        if output.sort_items_within_group == "alpha":
            items = sorted(items, key=lambda x: x[1].lower())
        for r, name in items:
            line = _render_line(
                output.line_format,
                element_name=name,
                element_id=r.token_id,
                sum_value=r.value,
                bucket=r.bucket,
            )
            if output.show_per_source_breakdown:
                line += _render_breakdown(output.breakdown_format, r.sources)
            if output.include_provenance:
                # ADR-217: trailing HTML comment carrying the row's
                # element_id. Appended LAST so it never interrupts the
                # visible text or any per-source breakdown.
                line += f" <!-- iris:element={r.token_id} -->"
            out_lines.append(line)
            row_count += 1
        out_lines.append("")
    return "\n".join(out_lines).rstrip() + "\n", row_count


# ─────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────


async def run(
    db: DatabasePort,
    *,
    profile_id: str,
    source_diagram_id: str,
) -> AggregationResult:
    """Apply ``profile_id`` to ``source_diagram_id``. See SPEC-212-b."""
    profile_row = await get_aggregation_profile(db, profile_id)
    if profile_row is None:
        raise AggregationProfileNotFound(profile_id)
    p = ProfileData(**profile_row["profile_data"])

    # Sanity: source must exist.
    src_name, src_version = await _diagram_meta(db, source_diagram_id)
    if src_name is None:
        raise AggregationSourceNotFound(source_diagram_id)

    accumulator: list[_Row] = []
    source_versions: dict[str, int] = {source_diagram_id: src_version or 0}
    warnings: list[str] = []

    source_markdown = await _read_smart_markdown_source(db, source_diagram_id)

    if p.traversal.outer is not None:
        # Two-level walk.
        outer = p.traversal.outer
        for tok in _parse_tokens(source_markdown, outer.collect_token_type):
            ref_id = tok.entity_id
            inner_md = await _read_smart_markdown_source(db, ref_id)
            ref_name, ref_version = await _diagram_meta(db, ref_id)
            if ref_name is None:
                warnings.append(
                    f"Skipping deleted outer reference {outer.collect_token_type}:{ref_id}",
                )
                continue
            source_versions[ref_id] = ref_version or 0
            multiplier = await _resolve_multiplier(db, tok, ref_id, outer)
            await _collect_inner(
                db, inner_md, p.traversal.inner, multiplier,
                source_label=ref_name,
                accumulator=accumulator, warnings=warnings,
            )
    else:
        # Single-level walk.
        await _collect_inner(
            db, source_markdown, p.traversal.inner, 1.0,
            source_label=src_name,
            accumulator=accumulator, warnings=warnings,
        )

    grouped = _group_and_aggregate(accumulator, p.output.aggregation_fn)
    markdown, row_count = await _format_output(db, grouped, p.output)

    return AggregationResult(
        markdown=markdown,
        computed_at=datetime.now(tz=UTC).isoformat(),
        source_versions=source_versions,
        row_count=row_count,
        warnings=warnings,
    )
