# SPEC-213-b: Aggregation_list source + profile pickers

Implements: [ADR-213](../ADR-213-Aggregation-List-Diagram-Type.md) — the deferred UI pickers from SPEC-213-a §3.

## 1. Component

New `frontend/src/lib/canvas/text/AggregationListCanvas.svelte`:

- **View mode**: renders `data.content` via `MarkdownView` (same look as `smart_markdown` / `dynamic_list`).
- **Edit mode**: shows a config pane with:
  - **Source diagram** `<select>` listing smart_markdown diagrams in the same set (`GET /api/diagrams?set_id=<id>&page_size=200`, filtered client-side to `diagram_type === 'smart_markdown'`).
  - **Aggregation profile** `<select>` listing in-scope profiles (`GET /api/aggregation/profiles?set_id=<id>&include_global=true`).
  - Collapsible **Preview** (the current rendered output) — read-only; a re-render happens after Save.

Selecting a value emits `onsourcechange({source_diagram_id, profile_id})` which the parent (`views/[id]/+page.svelte`) writes into `diagram.data` and marks `canvasDirty`.

## 2. Dispatcher

`views/[id]/+page.svelte` gains an `aggregation_list` branch in both the edit-mode and browse-mode canvas dispatchers. Browse mode renders content only; edit mode uses the config pane.

## 3. Create flow

`DiagramDialog.svelte`'s `markdown` notation gets a new entry: `{ value: 'aggregation_list', label: 'Aggregation list' }`. Create produces a skeleton diagram with no `data.source_diagram_id` / `data.profile_id`. The user then opens the new diagram in edit mode to pick source + profile.

This matches how `smart_markdown` and `dynamic_list` work — the create dialog is type/name/notation only; per-type config lives on the canvas.

## 4. Genericness

The component is generic — no recipe/meal/etc. terminology in code paths. The dropdowns surface whatever the user has created/seeded. The same canvas serves any aggregation use case.

## 5. Tests

`frontend/tests/unit/aggregationListCanvas.test.ts` covers:

- The diagram-list filter (only `smart_markdown` diagrams).
- The profile-list query shape (set_id + include_global).
- The `onsourcechange` emit shape.
- The view-mode / edit-mode dispatch.

## 6. Out of scope

- Typeahead autocomplete on the source / profile pickers (current = native `<select>`; sufficient when set sizes are small).
- Cross-set source picking (current: same-set only).
- Live engine re-render on every config change (current: triggers on Save like other canvases).
