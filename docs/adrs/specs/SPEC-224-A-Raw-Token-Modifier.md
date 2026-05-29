# SPEC-224-A: Smart-markdown `:raw` modifier

Implements **[ADR-224](../ADR-224-Raw-Token-Modifier.md)**.

## Grammar

Any smart-markdown token's field-spec gains an optional trailing `:raw`
modifier:

```
{{<entity-type>:<id>:<field-spec>[:raw]}}
```

With `:raw` present, the resolver returns the **plain string value**.
Without it, the existing ADR-209 link-wrapped form is returned
unchanged.

## Code anchors

- `backend/app/diagrams/smart_markdown.py`:
  - `_resolve_one` strips a trailing `:raw` from `field_spec` **before**
    the ADR-221 `detail_diagram` short-circuit and **before** the
    ADR-210 `=value` override split, then sets a `raw_mode` flag for
    the wrap step.
  - At the wrap step, when `raw_mode` is true the resolved value is
    returned plain (not wrapped in `[…](iris://…)`).
  - `_resolve_element_detail_diagram(..., raw_mode=False)` honours the
    flag and returns the target diagram name unwrapped when set.
- Aggregation engine: unchanged. Its values are already unwrapped.

## Composition

- `{{element:<id>:name:raw}}` → `Cyber Security`
- `{{element:<id>:meta:status:raw}}` → `Approved`
- `{{element:<id>:relationship_count:raw}}` → `19`
- `{{diagram:<id>:element_count:raw}}` → `13`
- `{{element:<id>:detail_diagram:raw}}` → `CSE.00 Security capability zone`
- `{{element:<id>:attr:attributes/Capabilities/type=10:raw}}` → `10`
  (the ADR-210 override still applies; the `:raw` strip happens first)
- Token without `:raw` keeps existing wrap behaviour (regression).

## Acceptance criteria

1. A token ending in `:raw` resolves to the plain string value (no
   `iris://` link in the output).
2. A token without `:raw` keeps the existing link-wrap behaviour
   verbatim.
3. The modifier composes with `meta:`, `tag:`, `attr:`, `:element_count`,
   `:detail_diagram`, the ADR-210 `=value` override, and the ADR-222
   `diagram:<id>:element_count`.

## Tests

`backend/tests/test_diagrams/test_smart_markdown.py`:
- `test_raw_modifier_returns_unwrapped_name`
- `test_raw_modifier_with_meta_status`
- `test_raw_modifier_with_diagram_element_count`
- `test_raw_modifier_with_detail_diagram`
- `test_without_raw_modifier_still_wraps` (regression)
