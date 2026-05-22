# ADR-210: Smart-markdown token `=value` overrides and blank-attribute editable spans

Status: Accepted (2026-05-22)

Builds on: [ADR-205](./ADR-205-Smart-Markdown-View-Type.md), [ADR-206](./ADR-206-Smart-Markdown-Picker-Evolution.md).

## Context

Smart_markdown today resolves entity field tokens against the stored value on the referenced entity. Per-use values — a recipe saying "500 g of pork mince *for this dish*" — have no first-class place to live. Users hand-write the quantity as free text prefix:

```
- 500 {{element:UUID:attr:attributes/Unit/type}} {{element:UUID:name}}
```

This works for human readers but the `500` is plain prose, not structured data. Any downstream feature that needs to consume those numbers — most immediately, the aggregation engine that will build the shopping list for [issue #211](https://github.com/cgbarlow/iris/issues/211) — would have to parse natural language ("500g", "1/2 cup", "a pinch") out of arbitrary markdown. Brittle.

Three options were considered:

1. **Migrate recipes to Recipe elements with `Recipe -[contains]-> Ingredient` relationships, qty/unit on relationship.data.** Clean structurally but loses the recipe-as-document UX (cooking method, photos, notes interleaved with ingredients), and forces a one-shot rewrite of all existing recipes into element-graph form.

2. **Add a domain-specific token type — `{{ingredient:UUID:qty:500}}`.** Compact and machine-readable, but bakes "ingredient" semantics into Iris core, violating the genericness invariant ([ADR-214](./ADR-214-Genericness-Invariant-Shopping-List.md)).

3. **Extend the existing attribute-reference token with an inline `=value` override.** Same grammar shape, generic, machine-parseable, additive.

(1) and (2) are rejected — (1) for UX cost, (2) for genericness. (3) — this ADR — wins.

## Decision

Extend ADR-205's token grammar with an inline value-override suffix on attribute references:

```
{{<entity-type>:<id>:<field-spec>}}              → existing form, resolves stored value
{{<entity-type>:<id>:<field-spec>=<value>}}      → new form, uses <value> verbatim
{{<entity-type>:<id>:<field-spec>=}}             → new form, empty value = "fillable slot" marker
```

The override applies to any `field-spec` (name, description, `attr:<path>`) and any non-image entity type. Image tokens are unaffected (ADR-209 grammar is unchanged).

### Resolver precedence

1. If `field-spec` contains `=`:
   - Split on the **first** `=` only. Everything after is the override value. (Values can contain `=`; paths cannot.)
   - **Non-empty override** → return the override value, wrapped in the same `[text](iris://<type>/<id> "<entity-name>")` link the resolver already emits for stored values. The link still points at the source entity; the text is the per-use value.
   - **Empty override** (`...field-spec=`) → return `None`. The token then renders as `~~{{...}}~~` strikethrough. This is the **fillable slot** marker — author has declared "this is a slot to fill in," and strikethrough makes the unfilled slot visible.
2. If `field-spec` has no `=` → existing behaviour: look up the stored value; `None` if missing/empty → strikethrough.

### Entity existence still checked

Even when an override is present, the resolver looks up the entity to populate the link's `title` attribute. If the entity is deleted/missing, the token renders as strikethrough regardless of override — dangling references shouldn't masquerade as resolved just because they carry a value.

### Canvas editing behaviour

`SmartMarkdownCanvas.svelte` in **edit mode** detects tokens whose override is empty (the fillable-slot form) and renders them as inline `<input>` elements styled to fit inline with the surrounding markdown. On blur, the canvas rewrites the token in `data.markdown_source` from `...=` to `...=<value>` and re-runs the resolver against the updated source.

The picker (ADR-206) gains a new option in the field-step: **"Insert as fillable placeholder"** — inserts the token with a trailing `=` so the author can fill it later (or leave blank for the next person).

### Source-pane fallback

The source pane (raw `data.markdown_source` textarea) is the always-available edit path; users can type or paste `...=500` directly. The inline-editable span is a quality-of-life affordance, not a requirement.

## Consequences

**Positive:**

- Structured per-use values without any new entity-type variant. Same regex shape; same resolver dispatch.
- Downstream consumers (aggregation engine, MCP tools, exports) can parse `=value` from the token string deterministically — no NL parsing.
- The fillable-slot marker (`...=`) is a visible UI affordance distinct from "value resolved" and "entity missing."
- Composes with element-template stamps ([ADR-211](./ADR-211-Element-Template-Stamps.md)) — a stamp can include `{{self:attr:Quantity/type=}}` and every element minted via the stamp is born ready to be filled in.
- Renders identically to today's free-text-quantity pattern, so existing recipes continue to read the same after migration ([§4.7 of the plan](../plans/issue-211-shopping-list-implementation.md)).

**Negative / accepted trade-offs:**

- Attribute paths cannot contain `=` (paths walk dotted JSON keys, which by convention don't carry `=`). Documented in SPEC-210-a; resolver splits on first `=`.
- A blank stored attribute and a fillable-slot marker are visually identical in render (both strikethrough). The intent distinction (author-declared vs. data-missing) lives only in the source. Acceptable — both need user attention; the render's job is to signal "look here," which strikethrough does.
- `style` attribute is not added to the inline `<input>` directly via Svelte text rendering — input is a real DOM element bound by the canvas, not produced by the resolver. No new `{@html}` paths (protocol §7).

## References

- [ADR-205](./ADR-205-Smart-Markdown-View-Type.md) — original token grammar.
- [ADR-206](./ADR-206-Smart-Markdown-Picker-Evolution.md) — picker hierarchical browse + subtree search; this ADR adds one new field-step option.
- [ADR-209](./ADR-209-Entity-Image-Attachments.md) — `image` token variant, unaffected.
- [SPEC-210-a-Smart-Markdown-Value-Overrides.md](./specs/SPEC-210-a-Smart-Markdown-Value-Overrides.md) — grammar regex, resolver pseudocode, canvas behaviour spec, test matrix.
- [`docs/plans/issue-211-shopping-list-implementation.md`](../plans/issue-211-shopping-list-implementation.md) §2 — placement in the overall plan.
