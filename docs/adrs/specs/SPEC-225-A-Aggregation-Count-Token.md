# SPEC-225-A: Smart-markdown `aggregation` token

Implements **[ADR-225](../ADR-225-Aggregation-Count-Token.md)**.

## Grammar

New entity type ``aggregation`` whose id is an ``aggregation_list``
diagram id. Single supported field-spec ``group_count:<group_value>``:

```
{{aggregation:<aggregation_list_view_id>:group_count:<group_value>[:raw]}}
```

- `<group_value>` is matched against the group string produced by the
  bound profile's `output.group_by`. Match is case-sensitive, exact,
  trimmed.
- `:raw` (from ADR-224) is honoured and strips the iris:// link wrap.

## Examples

- `{{aggregation:d3a6aa0c-…:group_count:Approved}}` → `[7](iris://…)`
- `{{aggregation:d3a6aa0c-…:group_count:Approved:raw}}` → `7`
- `{{aggregation:73508bc9-…:group_count:3:raw}}` → `15` (Maturity, level 3)

## Resolution path

1. Look up the diagram by id (live, not deleted).
2. Require `diagram_type == "aggregation_list"`. Anything else → `None`.
3. Read `data.source_diagram_id` and `data.profile_id`. Either missing
   → `None`.
4. Call `aggregation.engine.run(db, profile_id=…, source_diagram_id=…)`.
5. For each row in the engine result, compute the group value via
   `_resolve_group_value` (already used by the engine output stage).
   Count rows whose group equals `<group_value>`.
6. Return that count as a string.

Unknown group (not present in results) returns ``"0"``. View
missing/deleted/not-aggregation_list returns ``None`` (strikethrough,
matching the existing dangling-reference UX).

## Code anchors

- `backend/app/diagrams/smart_markdown.py`:
  - `_TOKEN_RE` (or equivalent dispatcher) extended to accept
    ``aggregation`` as an entity_type.
  - `_resolve_one` gains an `aggregation` branch that delegates to a
    new `_resolve_aggregation_group_count(db, view_id, group_value)`
    helper.
  - Helper imports `app.aggregation.engine` lazily (avoid import
    cycles, mirroring the lazy import in `app.diagrams.service.get_diagram`
    ADR-213 aggregation_list hook).
  - When `raw_mode` is true, the count is returned plain (no link
    wrap) — same composition rule as ADR-224.
- `backend/app/aggregation/engine.py`: no algorithm change. Re-uses
  `run(...)` and (where helpful) `_resolve_group_value`.

## Composition

- With `:raw` for Mermaid pie / bar / flowchart values.
- Inside element/diagram tables and prose lines.
- Outside fenced code blocks the default form (link-wrapped) lands the
  reader on the aggregation_list view itself (`iris://diagram/<view_id>`).

## Acceptance criteria

1. A token with a valid aggregation_list view id and an existing group
   returns the row count for that group.
2. A token whose group does not exist in the results returns `"0"`.
3. A token whose view id is missing/deleted, points at a non-
   aggregation_list diagram, or whose view is missing
   `source_diagram_id`/`profile_id`, resolves to `None`
   (strikethrough).
4. `:raw` strips the link wrap on the count.
5. Default form wraps the count in `[N](iris://diagram/<view_id>)`.

## Tests

`backend/tests/test_diagrams/test_smart_markdown.py`:
- `test_aggregation_group_count_returns_named_group_count`
- `test_aggregation_group_count_unknown_group_returns_zero`
- `test_aggregation_group_count_missing_view_strikethrough`
- `test_aggregation_group_count_non_aggregation_list_diagram_strikethrough`
- `test_aggregation_group_count_raw_returns_unwrapped`
- `test_aggregation_group_count_default_wraps_link_to_view`
