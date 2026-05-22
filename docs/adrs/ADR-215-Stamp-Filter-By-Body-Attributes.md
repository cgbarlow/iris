# ADR-215: Stamp scope filter — body-parsing attribute match

Status: Accepted (2026-05-22)

Builds on: [ADR-211](./ADR-211-Element-Template-Stamps.md), [SPEC-211-a](./specs/SPEC-211-a-Element-Template-Stamps.md), [ADR-214](./ADR-214-Genericness-Invariant-Shopping-List.md).

## Context

Per SPEC-211-a §3, `GET /api/element-templates/stamps?element_id=<id>` filters stamps to those in-scope for the element via two checks:

1. Scope (global or matching set).
2. `template_data.element_type` matches the element's `element_type` (or the template doesn't carry an `element_type`).

In the real Iris data, almost every domain element is `element_type = "class"` (grocery items, stories, log entries — all class). The five seeded stamps all target `element_type=class`. Net effect: in the smart-markdown picker, a user drilling into a "sausages" element sees all five stamps including "Sized story", which makes no sense for a grocery item.

The user-facing report ([issue #211 comment 2026-05-22](https://github.com/cgbarlow/iris/issues/211)) called this out: "picker is showing me stamp for 'sized story' [for a sausages element]". The `element_type` filter is too coarse.

## Decision

Add a third filter step: a stamp is in-scope for an element only when **every** attribute name referenced by the stamp's body (via `{{self:attr:attributes/<NAME>/<...>}}` tokens) is present on the element's `data.attributes` array.

```
required = { ATTR_NAME for every
             {{self:attr:attributes/ATTR_NAME/<rest>}} token
             in stamp.markdown_stamp }
element_attrs = { a["name"] for a in element.data.attributes
                  if a is a dict with a "name" key }
stamp_in_scope_by_body  = required ⊆ element_attrs
```

A stamp whose body references no `attr:` tokens (e.g. just `{{self:name}}`) passes the body filter trivially — falls back to the pre-existing `element_type` check only.

### Why body-parsing, not template_data blueprint

The template's `template_data.data.attributes` is a snapshot of *every* attribute the source element had at template-creation time. A stamp captured from a sausage element would have Quantity, Unit, Products, Preferred product in its blueprint — but the stamp body usually references only some of them (e.g. Quantity + Unit + name).

Using the blueprint as the required-attributes set would over-constrain: the same "qty + unit + name" stamp would only show up on elements that *also* have Products and Preferred product. Way too narrow — a user wanting to write `{{self:attr:attributes/Quantity/type=}} {{self:attr:attributes/Unit/type}} {{self:name}}` against a butter element (no Products attribute) would be denied.

The stamp **body** is the authoritative statement of which attributes the stamp will actually render. Anything not referenced by the body doesn't matter.

### Why not "any-of" or tag-based

- **Any-of** (stamp shown if at least one referenced attribute is on the element) — admits noise: a generic element with one of many attributes would get unrelated stamps. We want precision.
- **Tag-based** matching (manual user tags) — new authoring burden; harder to seed; doesn't reuse existing data. Rejected.

## Consequences

**Positive:**

- The user's reported bug closes — sausage shows only the Ingredient/"Quantified item" stamp; story shows only Sized story; etc.
- The seeded blueprints (Quantity + Unit, Points, Hours, Amount + Currency, Pages + Author) become first-class — they define applicability through the stamp body authors will pick.
- Composes with the v6.24.0 stamp editor: a user editing a stamp body to add `{{self:attr:attributes/Difficulty/type}}` immediately narrows the stamp's applicability to elements that have Difficulty.
- No new database field, no new schema migration — pure filter logic on top of existing data.

**Negative / accepted trade-offs:**

- Stamps whose body deliberately uses no `attr:` tokens (only `name`/`description`) match any element that passes the element_type check. Reasonable: a "passing mention" stamp like `{{self:name}}` shouldn't be element-attribute-specific.
- A user can author a stamp body referencing an attribute that doesn't exist anywhere in their data; the stamp would then never appear. That's a discoverability issue, not a correctness one — author error surfaces by absence rather than failure. Documented in SPEC-211-d.

## Rejected alternatives

- **Blueprint-attribute filter** (rejected, see "Why body-parsing").
- **Manual `stamp_element_type_filter` column** on element_templates — codifies the same coarseness the user complained about, just at a more granular level. Doesn't address the real signal (which attributes the body uses).
- **Element-type sub-categorization** (e.g. `element_type` = "class:grocery" vs "class:story") — would require a data migration of every element. Body-parsing achieves the same precision without touching element data.

## References

- [SPEC-211-d — body-parsing algorithm, edge cases, tests](./specs/SPEC-211-d-Stamp-Filter-By-Body-Attributes.md)
- [SPEC-211-a §3](./specs/SPEC-211-a-Element-Template-Stamps.md) — the original element_type-only filter this ADR extends
- [`docs/plans/issue-211-comment-followups.md`](../plans/issue-211-comment-followups.md) §3 — plan record
