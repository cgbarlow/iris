# SPEC-223-A: Element metadata, EA tagged-value, and computed-count tokens

Implements **[ADR-223](../ADR-223-Element-Metadata-Tag-Count-Tokens.md)**.

## Smart-markdown field-specs (on `element` tokens)

| Field-spec | Resolves to | Notes |
|---|---|---|
| `meta:<key>` | `element.metadata[<key>]` as string | Empty / whitespace → strikethrough |
| `tag:<property>` | EA tagged value `metadata.tagged_values[where property==<property>].value` | Strips `#NOTES#…` suffix; `""` and `"-"` → strikethrough |
| `relationship_count` | `COUNT(*) FROM relationships WHERE (source_element_id=<id> OR target_element_id=<id>) AND is_deleted=0` | |
| `diagram_usage_count` | `COUNT(DISTINCT d.id) … data LIKE '%<id>%'` | Same metric as `elements/service.get_element` |

Resolved values pass through `_resolve_one`'s ADR-209 link wrapping → the
output is an `iris://element/<id>` markdown link with the value as the
visible text.

## Aggregation engine paths (`value_attribute_path` / `bucket_attribute_path`)

`/`-form on `element` tokens:

| Path | Resolves to |
|---|---|
| `meta/<key>` | metadata key |
| `tag/<property>` | tagged value (with `#NOTES#` strip + `-`/empty → None) |
| `relationship_count` | computed count |
| `diagram_usage_count` | computed count |

Anything else falls through to the existing `element.data` walker.

## Aggregation engine `output.group_by`

Dot-form, prefixed `element.`:

| `group_by` | Group key |
|---|---|
| `element.meta.<key>` | metadata key |
| `element.tag.<property>` | tagged value |
| `element.relationship_count` | computed count (stringified) |
| `element.diagram_usage_count` | computed count (stringified) |

Existing `element.name`, `element.package_name`, `element.attributes.*`
all keep working.

## Code anchors

- `backend/app/diagrams/smart_markdown.py`:
  - `_parse_metadata`, `_extract_tagged_value`,
    `_fetch_element_relationship_count`,
    `_fetch_element_diagram_usage_count` — new shared helpers.
  - `_fetch_element_field` — branches on the new field-specs; selects
    `ev.metadata` alongside name/description/data.
- `backend/app/aggregation/engine.py`:
  - Imports the helpers above (§13 DRY).
  - `_fetch_element_metadata_dict` — engine-side metadata reader.
  - `_resolve_token_value` — branches on `meta/`, `tag/`,
    `relationship_count`, `diagram_usage_count` before falling through to
    the existing data walker.
  - `_resolve_group_value` — branches on `meta.`, `tag.`, and the two
    counts before falling through to the existing `attributes.` walker.

## Acceptance criteria

1. `{{element:<id>:meta:<key>}}` renders the metadata value, linked to
   the element; missing key strikes through.
2. `{{element:<id>:tag:<property>}}` returns the tagged value with the
   `#NOTES#` suffix stripped; empty / `-` → strikethrough.
3. `{{element:<id>:relationship_count}}` and
   `{{element:<id>:diagram_usage_count}}` render the computed counts.
4. Aggregation profiles can `value_attribute_path` and `group_by` against
   any of the new paths. End-to-end: sum `relationship_count` grouped by
   `element.meta.status` produces a per-status breakdown.

## Tests

- `backend/tests/test_diagrams/test_smart_markdown.py` — six new cases
  cover each field-spec and its strikethrough fallback.
- `backend/tests/test_aggregation/test_engine.py` — two integration
  tests exercise the new value/group paths end-to-end.
