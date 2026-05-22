# SPEC-211-c: Element-template stamp editor

Implements: [ADR-211](../ADR-211-Element-Template-Stamps.md) — the deferred stamp authoring UI from SPEC-211-a §8.

## 1. Behaviour

The element-template detail page (`frontend/src/routes/element-templates/[id]/+page.svelte`) gains a new **Markdown stamp** section showing the template's `markdown_stamp` body. The section is editable:

- **Add stamp** / **Edit stamp** button → inline textarea editor.
- **Save stamp** button → `PUT /api/element-templates/{id}` with `{ markdown_stamp: <body> }`. Submits an empty string to clear.
- **Cancel** button → reverts to the persisted value.

The textarea is a plain text editor. Stamp authors write `{{self:…}}` tokens by hand. Placeholder text and a help paragraph above the textarea document the syntax and link to the trailing-`=` fillable-slot convention from ADR-210.

## 2. Why a plain textarea, not the full smart-markdown picker

A picker-driven self-mode editor (the original SPEC-211-a §8 idea) would require:

- Adding `selfMode: boolean` to `SmartMarkdownCanvas.svelte` and through to `SmartMarkdownSlashPicker.svelte`.
- A new picker code path that skips the entity-browse step and emits `{{self:<field-spec>}}` tokens.
- A live-preview pass that substitutes `self` → `source_element_id` and runs the smart-markdown resolver.

That's a substantial picker rework with rendering-side risk (live preview vs. saved render). For v6.24.0 the goal is **enable in-browser stamp authoring at all** — the textarea covers it. Seeded stamps are good templates; users clone them with a quick paste-and-edit. The picker self-mode is a future v6.25+ enhancement.

## 3. UI

```
─── Markdown stamp ────────────────────────────────────── [Edit stamp]
Smart-markdown fragment surfaced in the picker when this template is
in scope for the selected element (ADR-211). Use {{self:name}}, …

┌────────────────────────────────────────────────────────┐
│ {{self:attr:attributes/Quantity/type=}}                │
│  {{self:attr:attributes/Unit/type}} {{self:name}}      │
│                                                        │
└────────────────────────────────────────────────────────┘
                                       [Cancel] [Save stamp]
```

When not editing, the persisted body renders in a read-only `<pre>` block; when no stamp is set, a "No stamp set." muted line.

## 4. Persistence

- `PUT /api/element-templates/{id}` body `{ markdown_stamp: <body> }`.
- Backend (v6.19.0) accepts this as a partial update; sets the field; returns the updated template. The page reuses the response to refresh local state.
- Setting `markdown_stamp` to `""` (empty string) clears it. Setting to a non-empty whitespace-only string is treated as set (current backend semantics — kept for v1; tightening can come later).

## 5. Test

`frontend/tests/unit/stampEditor.test.ts` covers:

- The PUT request body shape (`{markdown_stamp: <body>}`).
- Round-trip: response with `markdown_stamp` populated updates the local `tpl` state.
- Empty-string clears the stamp (request body shape).
- Whitespace-only is sent verbatim.

Per the project's frontend testing posture, this is a data-shape / business-rule test, not a full component render.

## 6. Out of scope (deferred to a future v6.25+ PR)

- Picker self-mode (emits `{{self:…}}` tokens via the smart-markdown picker UI).
- Live preview of the stamp rendered against the template's source element.
- "Manage stamps" link from the smart-markdown picker footer.
- Stamp validation (e.g. warn on `{{element:…}}` tokens that should be `{{self:…}}`).
