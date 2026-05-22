# SPEC-212-b: Aggregation engine

Implements: [ADR-212](../ADR-212-Aggregation-Profiles-And-Engine.md)

## 1. Module layout

```
backend/app/aggregation/
  __init__.py
  models.py                  # pydantic — see SPEC-212-a
  schema.py                  # JSONSchema for profile_data
  profiles_service.py        # CRUD — see SPEC-212-a
  engine.py                  # the kernel (this spec)
  attribute_resolver.py      # walk dotted attribute paths
  format_renderer.py         # render line / breakdown / group templates
  routes.py                  # FastAPI — see SPEC-212-c
  exceptions.py
```

## 2. Public function

```python
async def run(
    db: DatabasePort,
    *,
    profile_id: str,
    source_diagram_id: str,
) -> AggregationResult:
    """Apply the named profile to the source diagram. Returns the
    computed markdown and the source-version stamps that were observed
    during the walk (so consumers can detect staleness).
    """
```

Where `AggregationResult` is:

```python
class AggregationResult(BaseModel):
    markdown: str
    computed_at: str
    source_versions: dict[str, int]   # diagram_id -> current_version observed
    row_count: int
    warnings: list[str] = []
```

## 3. Algorithm

```python
async def run(db, *, profile_id, source_diagram_id):
    profile = await profiles_service.get_aggregation_profile(db, profile_id)
    if profile is None:
        raise ProfileNotFound(profile_id)
    p = ProfileData(**profile["profile_data"])

    accumulator: list[Row] = []
    source_versions: dict[str, int] = {}
    warnings: list[str] = []

    source_markdown = await _read_smart_markdown_source(db, source_diagram_id)
    source_versions[source_diagram_id] = await _diagram_version(db, source_diagram_id)

    if p.traversal.outer:
        # Two-level walk: outer tokens in the source point at sub-diagrams.
        for tok in _iter_tokens(source_markdown, p.traversal.outer.collect_token_type):
            ref_id = tok.entity_id
            multiplier = _resolve_multiplier(db, tok, ref_id, p.traversal.outer.multiplier)
            inner_md = await _read_smart_markdown_source(db, ref_id)
            source_versions[ref_id] = await _diagram_version(db, ref_id)
            await _collect_inner(db, inner_md, p.traversal.inner, multiplier,
                                 source_label=await _diagram_name(db, ref_id),
                                 accumulator=accumulator, warnings=warnings)
    else:
        # Single-level walk.
        await _collect_inner(db, source_markdown, p.traversal.inner, 1.0,
                             source_label=await _diagram_name(db, source_diagram_id),
                             accumulator=accumulator, warnings=warnings)

    grouped = _group_and_aggregate(accumulator, p.output.aggregation_fn)
    output_groups = await _group_for_output(db, grouped, p.output.group_by)
    markdown = format_renderer.render(output_groups, p.output)

    return AggregationResult(
        markdown=markdown,
        computed_at=datetime.now(tz=UTC).isoformat(),
        source_versions=source_versions,
        row_count=sum(len(g) for g in output_groups.values()),
        warnings=warnings,
    )
```

## 4. Token iteration

Uses the existing `_TOKEN_RE` regex from `backend/app/diagrams/smart_markdown.py` (DRY §13 — import, don't reimplement). For each match, parse:

- `entity_type` (group 1)
- `entity_id` (group 2)
- `field_spec` (group 3, optional)

If `field_spec` contains `=`, split on first `=` per ADR-210; the override is captured as `token.override`. The override and any subsequent attribute lookup feed into `_resolve_attribute` (see §5).

## 5. Attribute resolution (`attribute_resolver.py`)

Three callable resolvers:

```python
async def resolve_token_value(
    db, token, attribute_path, override_takes_precedence=True
) -> str | None:
    """Return the value for the token at attribute_path. Order:
       1. If the token has a `=value` override on this exact path → value.
       2. Else look up entity's stored attribute at the path.
       Returns None if unresolved.
    """

async def resolve_diagram_data(
    db, diagram_id, field_path
) -> str | None:
    """Read `data.<field_path>` from the diagram's current version's
    data JSON. Dotted path, walks dicts."""

async def resolve_group_by_field(
    db, token, group_by_path
) -> str | None:
    """Resolve a `group_by` config value like 'element.package_name' or
    'element.attributes.Unit/type' against the token's referenced
    entity. Returns '(none)' when missing."""
```

## 6. Multiplier resolution

```python
async def _resolve_multiplier(db, outer_token, ref_diag_id, rule):
    if rule is None:
        return 1.0
    numerator = None
    if rule.from_attribute_override:
        numerator = outer_token.override_for(rule.from_attribute_override)
    if numerator is None:
        numerator = rule.default_multiplier
    divisor = 1.0
    if rule.divisor_from_diagram_data:
        d = await resolve_diagram_data(db, ref_diag_id, rule.divisor_from_diagram_data)
        try:
            divisor = float(d)
        except (TypeError, ValueError):
            divisor = 1.0
    try:
        return float(numerator) / divisor if divisor else 1.0
    except (TypeError, ValueError):
        return 1.0
```

## 7. Grouping + aggregation

```python
def _group_and_aggregate(rows, fn):
    grouped = defaultdict(list)
    for r in rows:
        grouped[(r.token_id, r.bucket)].append(r)
    out = []
    for (token_id, bucket), items in grouped.items():
        sources = [(i.source_label, i.scaled_value) for i in items]
        if fn == "sum":
            value = sum(i.scaled_value for i in items)
        elif fn == "count":
            value = len(items)
        else:
            value = sum(i.scaled_value for i in items)
        out.append(GroupedRow(
            token_id=token_id, bucket=bucket, value=value, sources=sources,
        ))
    return out
```

## 8. Output formatting (`format_renderer.py`)

Format strings use `{placeholder}` syntax with Python str.format-style replacement:

| Placeholder | Source |
|---|---|
| `{element.name}` | the looked-up entity name |
| `{element.id}` | the entity id |
| `{sum_value}` | aggregated numeric value (integer-friendly when whole) |
| `{bucket}` | the bucket value (empty when no bucket) |
| `{bucket_spaced}` | " <bucket>" when non-empty, "" when empty (prevents trailing space) |
| `{sources_joined}` | "Source1 N1, Source2 N2" — the source breakdown |

`group_by` headers use a fixed `## {group_value}\n` template (not configurable in v1).

## 9. Edge cases

- Empty source markdown → empty markdown output (no warnings).
- Source diagram missing → `DiagramNotFound` exception → 404 at the API layer.
- Profile-referenced inner attribute missing on every collected token → empty markdown, single warning ("no values collected").
- Numeric coercion: values that don't parse as float become `0` for `sum`, are still counted for `count`. Warning emitted with the offending token id.
- `bucket_attribute_path` is null → all rows share `bucket = ""` and the format string's `{bucket_spaced}` resolves to empty.

## 10. Performance

- Each diagram fetched once via a small cache keyed on `(diagram_id, version)`.
- Each element fetched once for `group_by` resolution.
- Token regex scanned once per source.
- No N+1 reads — outer-step diagram fetches are batched.

For the shopping-list demo (~30 recipes × ~10 ingredients), full computation is under 200ms on the typical Supabase round-trip budget.

## 11. Tests

`backend/tests/test_aggregation/test_engine.py`:

- Single-level walk + sum on a fixture meal-plan with two recipes sharing one element. Asserts: aggregated value = sum across recipes, single line emitted.
- Two-level walk with multiplier. Asserts: multiplier × inner values matches expected.
- Mixed buckets emit two lines per token (per Q3 — no cross-unit conversion).
- Blank value with `skip_blank_values=true` → row dropped, with warning.
- `group_by = element.package_name` → grouped output with `##` headers per package.
- `aggregation_fn = count` → integer count per (token, bucket).
- Dangling outer token (deleted diagram) → warning, no contribution.

`backend/tests/test_aggregation/test_seeded_profiles_smoke.py` — for each of the five seeded profiles, build a minimal fixture and assert the engine runs without raising. Asserts the seeded JSON validates against the schema. Does NOT assert specific output (output-format details are per-profile).
