# SPEC-226-A: Smart-markdown `aggregation:…:row_count` + `set:…:element_count`

Implements **[ADR-226](../ADR-226-Aggregation-Row-Count-And-Set-Element-Count-Tokens.md)**.

## Grammar

Two new field-specs on existing entity types:

```
{{aggregation:<aggregation_list_view_id>:row_count[:raw]}}
{{set:<set_id>:element_count[:raw]}}
```

- `:raw` (ADR-224) strips the iris:// link wrap.
- Default form wraps in `iris://diagram/<view_id>` /
  `iris://set/<set_id>`.

## Resolution

### `aggregation:<view_id>:row_count`

1. Look up the diagram; require live + `diagram_type ==
   "aggregation_list"` + `data.source_diagram_id` + `data.profile_id`.
   Any failure → `None` (strikethrough).
2. Call `aggregation.engine.run(...)` (same call ADR-225
   `group_count` already makes).
3. Return `result.row_count` as a string.

### `set:<set_id>:element_count`

1. `SELECT COUNT(*) FROM elements WHERE set_id = ? AND is_deleted = 0`.
2. If the set itself is missing/deleted → `None`. Otherwise return
   the count as a string (`"0"` if the set is empty but exists).

## Examples

- `{{aggregation:d3a6aa0c-…:row_count:raw}}` → `37`
  (Status rollup over all 37 capabilities)
- `{{aggregation:73508bc9-…:row_count:raw}}` → `37`
  (Maturity rollup)
- `{{set:7f2521de-…:element_count:raw}}` → `50`
  (every non-deleted element in the GEANZ Sparx set)
- `{{set:5036a71a-…:element_count}}` → wrapped link to the
  Aggregation Demo set page

## Code anchors

- `backend/app/diagrams/smart_markdown.py`:
  - `_resolve_one` aggregation branch (added by ADR-225) gains a
    second field-spec check: `field_spec == "row_count"` →
    `_resolve_aggregation_row_count(db, view_id, raw_mode)`.
  - `_resolve_one` `set` branch routes `field_spec == "element_count"`
    to a new `_fetch_set_element_count` helper before falling through
    to `_fetch_set_field`.
  - New `_resolve_aggregation_row_count` mirrors the existing
    `_resolve_aggregation_group_count` resolver: validates the view,
    runs the engine, returns `result.row_count`; wraps in
    `iris://diagram/<view_id>` unless `raw_mode`.
  - New `_fetch_set_element_count` runs the COUNT query, wraps in
    `iris://set/<set_id>` (tooltip = set name) unless `raw_mode`.

## Acceptance criteria

1. `aggregation:<view>:row_count` returns the engine's `row_count`
   total as a string. Composes with `:raw`.
2. `aggregation:<view>:row_count` on a missing / non-aggregation_list
   view → strikethrough.
3. `set:<id>:element_count` returns the count of non-deleted elements
   in the set as a string. `0` for an empty (but live) set.
4. `set:<id>:element_count` on a missing / deleted set →
   strikethrough.
5. `:raw` modifier suppresses link wrap on both tokens.
6. Default form wraps in `iris://diagram/<view_id>` and
   `iris://set/<set_id>` respectively, with the entity name as the
   link tooltip.

## Tests

`backend/tests/test_diagrams/test_smart_markdown.py`:
- `test_aggregation_row_count_returns_total`
- `test_aggregation_row_count_raw_returns_unwrapped`
- `test_aggregation_row_count_missing_view_strikethrough`
- `test_set_element_count_returns_live_count`
- `test_set_element_count_raw_returns_unwrapped`
- `test_set_element_count_missing_set_strikethrough`
- `test_set_element_count_excludes_deleted_elements`
