# ADR-207: Smart Markdown picker — bug fixes, container drill, KG colour alignment

Status: Accepted (2026-05-20)

Supersedes: nothing. Builds on [ADR-206](./ADR-206-Smart-Markdown-Picker-Evolution.md).

## Context

v6.15.0 shipped the new picker (hierarchical browse, drill mode, recent chips). User-acceptance testing surfaced four bugs and one UX gap in five comments on issue [#185](https://github.com/cgbarlow/iris/issues/185) (2026-05-20):

1. The picker badge says "diagram" (backend's internal name). The user-visible term in Iris is "view". Backend keeps `entity_type='diagram'`; only the picker's display label is wrong.
2. Badge colours don't align with the Knowledge Graph colour key (`frontend/src/lib/utils/graphColors.ts`). The picker uses the same pale palette but maps the colours to the wrong types.
3. Drill keystrokes (`.`/Tab/typing-to-filter) are broken in production. Mouse + arrow keys work; the IDE-style keystrokes don't.
4. Search input does nothing — typing has no effect on the results list.
5. Drilling into a non-element entity (package/set/collection) hides its children: the drill menu only offers `name`/`description`. The user wants children surfaced too, and a "Pick this {entity}" shortcut on browse-mode breadcrumb levels so a set or collection's own fields can be picked without descending out of the tree.

A sixth, unrelated bug landed in the same thread: the 'New' button in `HierarchyControls.svelte` is 1px shorter than the 'Show' button because of a border-vs-solid box-model mismatch.

## Decision

Five fixes, one CSS tweak, no breaking API changes:

### 1. Search regression — replace the `query`-untracked `$effect`

In v6.15.0 the search input wires to `query` via `bind:value` and a `$effect` re-fetches on input. Svelte 5's `$effect` only tracks reactive reads inside the function body. The block reads `mode` but not `query`, so it never re-runs when the user types. The v6.14.x version used `oninput={scheduleSearch}` directly on the input — restore that.

### 2. Drill keystroke regression — unconditionally `preventDefault` for `.` and Tab

`handleDrillKey` currently only calls `preventDefault()` on `.`/Tab/Enter when `menu.length > 0`. Tab without preventDefault tabs focus out of the picker entirely. `.` without preventDefault inserts a literal `.` into `drillFilter`. Once focus is lost, no further keystrokes work — which is why mouse+arrow continued to work but everything else was dead.

Fix: always preventDefault for `.` and Tab in drill mode, regardless of menu length. Enter keeps the existing `if menu.length > 0` gate. Empty menu + `.`/Tab is a no-op (the event is consumed but no drill happens).

### 3. Container drill for non-elements

Before: `enterDrill` for non-elements set `drillNode = { kind: 'empty' }` and exposed only the universal `name`/`description` shortcuts.

After: `enterDrill` branches on `entity_type`:

| Entity type | Children source | Menu contents |
|---|---|---|
| `element` | existing `/api/elements/{id}/data-tree` | name + description + walked-data fields |
| `collection` | `/api/picker/browse?scope=collection&collection_id=...` | name + description + each contained set |
| `set` | `/api/picker/browse?scope=set&set_id=...` | name + description + non-zero buckets (Elements/Packages/Views) |
| `package` | new `/api/picker/browse?scope=package&package_id=...` | name + description + contained elements |

Clicking a child container drills into that child (re-enters `enterDrill` with the child's `entity_type`). Backspace at the start of a segment pops the path; Backspace at the root of a child drill pops back to the parent's drill.

### 4. "Pick this {entity}" shortcut in browse mode

At non-root breadcrumb levels (`scope=collection`, `scope=set`, `scope=set_bucket`), render a "Pick this {label}" item at the top of the items list. Clicking it opens drill mode for the breadcrumb-leaf entity. The breadcrumb is the source of truth for what "this" refers to — no separate state.

### 5. KG colour alignment (badge palette rotation)

KG colours from `frontend/src/lib/utils/graphColors.ts` are:

| Type | KG hex |
|---|---|
| collection | `#ef4444` (red) |
| set | `#8b5cf6` (violet) |
| package | `#f59e0b` (amber) |
| diagram | `#22c55e` (green) |
| element | `#3b82f6` (blue) |

Keep the picker's existing pale palette but rotate the mappings so each type's badge tint matches its KG colour:

| Type | Was | Now | KG match |
|---|---|---|---|
| collection | `#f3e8ff` (pale purple) | `#fce7f3` (pale pink) | red |
| set | `#dcfce7` (pale green) | `#f3e8ff` (pale purple) | violet |
| package | `#fef3c7` (pale amber) | unchanged | amber |
| diagram | `#fce7f3` (pale pink) | `#dcfce7` (pale green) | green |
| element | `#dbeafe` (pale blue) | unchanged | blue |

A 3-way rotation (collection ↔ set ↔ diagram); package and element are already correct.

### 6. Diagram → View label inside the picker only

User wanted `diagram` → `view` everywhere in the UI, but on review constrained the scope to the new feature only (the picker) — the wider Iris rename will be a separate ticket. Specifically:

- Picker bucket label: "Diagrams" → "Views".
- Badge text for `entity_type='diagram'` rows: display label "view".
- Backend `entity_type` value and API paths unchanged.

This is a presentation-only mapping inside `SmartMarkdownSlashPicker.svelte`; no other file touches.

### 7. 'New' button height in HierarchyControls

The 'Show' button has a `border` (1px). The 'New' button uses a solid background with no border. The total box height differs by 1px. Add `border border-transparent` to the 'New' button — matches the 'Show' button's box model without visible border.

## Why these changes are bug fixes, not redesigns

All five picker issues are regressions on the v6.15.0 design captured in ADR-206. The behaviour the user expects is already documented there; the implementation just shipped with bugs. This ADR records the root-cause investigation and the fix shape so future regressions are easier to spot.

The container-drill change (item 3) is a behaviour extension. ADR-206 §6 "Drill UX" did not specify what `enterDrill` should do for non-elements — the picker landed with `{kind: 'empty'}` as a placeholder. This ADR fills that gap.

## Surface parity (§14)

All new endpoints are GETs (read-only). No new write surface, no MCP/CLI mirror needed.

## Consequences

- `frontend/src/lib/canvas/text/SmartMarkdownSlashPicker.svelte` — bug fixes + container drill + label/colour adjustments.
- `frontend/src/lib/components/HierarchyControls.svelte` — `border border-transparent` on 'New' button.
- `backend/app/search/router.py` — `/api/picker/browse` gains `scope=package` and `scope=package_bucket` (and a `package` step in the breadcrumb).
- Tests: regression guards in Vitest for search + drill keystrokes; backend tests for the new scopes.

CHANGELOG `[6.16.0]` Fixed/Changed/Added sections. No DB schema changes from this ADR. No §15 migration here (m072 belongs to ADR-208).

## Verification

Documented in SPEC-207-A's verification section.

## See also

- Issue [#185](https://github.com/cgbarlow/iris/issues/185) follow-up comments 2026-05-20.
- [ADR-206](./ADR-206-Smart-Markdown-Picker-Evolution.md) (the picker design this is fixing).
- `frontend/src/lib/utils/graphColors.ts` (KG colour key).
- §13 DRY, §14 Surface parity: `docs/protocols.md`.
