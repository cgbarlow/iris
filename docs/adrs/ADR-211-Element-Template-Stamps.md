# ADR-211: Markdown stamps on element templates

Status: Accepted (2026-05-22)

Builds on: [ADR-191](./ADR-191-Element-Templates.md), [ADR-205](./ADR-205-Smart-Markdown-View-Type.md), [ADR-206](./ADR-206-Smart-Markdown-Picker-Evolution.md), [ADR-210](./ADR-210-Smart-Markdown-Value-Overrides.md).

## Context

ADR-210 makes structured per-use values first-class in the smart-markdown grammar (`{{element:UUID:attr:path=500}}`). But composing the full "500 g Pork mince" recipe line still needs three tokens — quantity, unit, name — and three picker round-trips. For the user authoring 30+ recipes, that's tedious; for the `/goal`-driven shopping-list workflow ([issue #211](https://github.com/cgbarlow/iris/issues/211)) it's the friction point that pushes users back to free-text prose.

The existing `element_templates` machinery (ADR-191) already manages reusable artefacts scoped to a set or globally. It captures element fields for re-use at element-creation time, but has no concept of a *markdown snippet* to insert at recipe-authoring time.

## Decision

Add an optional `markdown_stamp TEXT` column to `element_templates`. The value is a smart-markdown fragment that may use a new `{{self:<field-spec>}}` token form — at insert time the picker substitutes `self` with the chosen element's actual ID, and the resulting fragment is placed at the cursor.

### `{{self:…}}` token

```
{{self:name}}                                       → {{element:UUID:name}}
{{self:attr:attributes/Quantity/type=}}             → {{element:UUID:attr:attributes/Quantity/type=}}
{{self:attr:attributes/Unit/type}}                  → {{element:UUID:attr:attributes/Unit/type}}
```

The grammar shape is identical to ADR-205's `<entity-type>:<id>:<field-spec>` but with the literal string `self` in place of `<id>` and a missing `<entity-type>`. `self` only appears inside a stamp's body; at insert time, the picker rewrites every `{{self:<field-spec>}}` to `{{element:<resolved-id>:<field-spec>}}`. The resolver never sees `self` tokens — they don't need to be valid against the existing `_TOKEN_RE` regex.

### Picker integration

When the smart-markdown picker has selected an entity, it queries `GET /api/element-templates/stamps?element_id=<id>` for in-scope stamps (a stamp is "in scope" when its template is global or matches the entity's set, and the template's captured `element_type` either matches the entity's `element_type` or was not captured at all). Stamps are displayed as a top section above the existing field-step menu. Picking a stamp emits its body with `self` substituted.

### Stamp authoring UX (deferred to v6.19.1)

A first-class stamp editor — smart-markdown editor in self-mode — is out of scope for v6.19.0. v6.19.0 ships the data model + picker integration + seeded global stamps; stamps can be authored via the existing element-template create/update endpoints (REST/MCP/CLI) by setting `markdown_stamp`. The richer UX comes in v6.19.1.

### Source-element optionality

ADR-191's `ElementTemplateCreate` required `source_element_id`. Stamps don't always have a source — a "Quantified item" stamp is a *type* of usage pattern, not a snapshot of a specific element. So `source_element_id` becomes optional. When absent, the caller supplies `template_data` directly (or leaves it empty); when present, the existing snapshot flow runs.

A template must declare a non-trivial purpose: at least one of `template_data` (non-empty) or `markdown_stamp` (non-empty) must be set. Pure no-op templates are rejected with HTTP 422.

### Scope semantics for stamps

The picker filters stamps for in-scope:

1. **Scope match**: `is_global = TRUE` OR `set_id` equals the selected entity's `set_id`.
2. **Element-type match**: if the template's `template_data` includes an `element_type`, it must equal the selected entity's `element_type`. If the template doesn't carry an `element_type`, the stamp is offered for any element type.

The second rule makes the stamp editor itself the place to constrain applicability — no separate `stamp_element_type_filter` column needed (this was the user's Q1 in the research-phase clarification).

### Seeds

Five global templates ship in the migration that adds the column ([§4.4](../plans/issue-211-shopping-list-implementation.md)). Each carries a `markdown_stamp` and a `template_data` blueprint (with blank attributes), so creating an element from the template yields the attribute slots the stamp expects:

| Template | Stamp |
|---|---|
| Quantified item | `{{self:attr:attributes/Quantity/type=}} {{self:attr:attributes/Unit/type}} {{self:name}}` |
| Sized story | `{{self:attr:attributes/Points/type=}} pts — {{self:name}}` |
| Logged work | `{{self:attr:attributes/Hours/type=}}h — {{self:name}}` |
| Line item | `{{self:attr:attributes/Currency/type}}{{self:attr:attributes/Amount/type=}} — {{self:name}}` |
| Read entry | `{{self:attr:attributes/Pages/type=}} pages — "{{self:name}}" by {{self:attr:attributes/Author/type}}` |

All five carry `is_global = TRUE`, `set_id = NULL`, `source_element_id = NULL`. The `template_data` for each is a pre-filled `{element_type: "class", notation: "simple", data: {attributes: [...]}}` blueprint.

## Consequences

**Positive:**

- One-pick insertion of multi-token chunks against any element. Picker round-trips drop from 3 → 1 for a "quantity unit name" line.
- Stamps are user-managed data, not Iris-core code — the genericness invariant (ADR-214) is preserved.
- Composes with ADR-210: stamps that contain `=` (fillable slots) deliver a "fill in the value" UX immediately on insertion.
- Five seeded global stamps cover the demo workflow and demonstrate the pattern for users to clone.

**Negative / accepted trade-offs:**

- ADR-191's `source_element_id` requirement is relaxed. Existing CHECK constraints still pass because the column was already nullable in the DB schema; the requirement was at the pydantic-model level. Backward-compatible.
- Stamp authoring without a richer UI (deferred to v6.19.1) means users editing stamps via API need to know the `{{self:…}}` syntax. Seeded stamps cover the common cases; doc'd in the spec.

## Rejected alternatives

- **Per-element `markdown_stamp` column.** Each element could carry its own stamp. Rejected: stamps are *type-of-usage* patterns reused across many elements; living on the template (which is the type registry) matches the conceptual model.
- **Separate `element_stamps` table.** Cleaner separation but duplicates the scope (`is_global`, `set_id`) and management UX that `element_templates` already provides. DRY violation (§13).
- **New `{{stamp:<stamp-id>}}` token form.** Late-binding by storing stamp ID in the markdown. Rejected: each diagram would silently re-resolve the stamp on every read, making the stored markdown opaque and hard to edit. Stamps are a paste-once author-time convenience, not a runtime reference.

## References

- [ADR-191](./ADR-191-Element-Templates.md) — original template model.
- [ADR-210](./ADR-210-Smart-Markdown-Value-Overrides.md) — `=value` overrides (used by the seeded stamps).
- [SPEC-211-a-Element-Template-Stamps.md](./specs/SPEC-211-a-Element-Template-Stamps.md) — schema, substitution algorithm, endpoint shape, seed table.
- [`docs/plans/issue-211-shopping-list-implementation.md`](../plans/issue-211-shopping-list-implementation.md) §4.4 — full seed table.
