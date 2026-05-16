# ADR-186: Dynamic List diagram type — auto-generated markdown surface

Status: Accepted (2026-05-16)
Extends: [ADR-137](ADR-137-Text-Diagram-Class.md) (Markdown notation)

## Context

Issue [#147](https://github.com/cgbarlow/iris/issues/147) — "Feature:
new markdown notation diagram/view type called 'dynamic list'." Three
comments refined the requirement:

1. Original body — auto-rendered bullet list driven by element
   relationships on the current diagram; not editable in the
   content-canvas sense; export as a markdown file.
2. Linked to #149 — two modes: default uses intra-diagram element
   relationships; alternative uses elements that belong to a given
   package. Mode 2 depends on ADR-184's `element.package_id` column.
3. Added a "Show description" toggle that appends each element's
   description in brackets after its name (both modes).

Plan-time AskUserQuestion clarifications:

- Default-mode bullet shape is **just the element name**, no
  relationship verb.
- Each intra-diagram relationship contributes **two** bullets in order
  (source then target). Elements participating in N relationships
  appear 2N times — explicitly non-deduplicated.
- The standard "Edit" button is enabled, but the canvas content stays
  read-only. Edit mode exposes a "Source" panel for mode / package /
  show_description selection.

## Decision

Register a new diagram_type `dynamic_list` under the existing `markdown`
notation (ADR-137, m044). Source-of-truth for compute config lives in
the diagram's existing `data` JSON under a `data.dynamic_source` key —
no schema changes to `diagrams` or `elements`. The rendered markdown is
synthesised at read-time (see [ADR-187](ADR-187-Synthesised-Content-On-Read.md))
so the existing export pipeline picks it up unchanged.

### Registry seed

Migration `m065_dynamic_list_diagram_type.py` inserts:

```python
_DIAGRAM_TYPE = ("dynamic_list", "Dynamic List", "Auto-generated markdown bullet list", 16)
_MAPPINGS = [("dynamic_list", "markdown", 0)]
```

`is_default=0` because the `markdown` notation already defaults to
`text` (m044). `display_order=16` slots immediately after `text` (15).

### `data.dynamic_source` shape

Three keys, all stored on the diagram's `data` JSON:

```json
{
  "dynamic_source": {
    "mode": "diagram_relationships" | "package_elements",
    "package_id": "<uuid>" | null,
    "show_description": false
  }
}
```

Defaults applied at compute time when any key is missing
(backwards-compat with diagrams created before this field shipped):
mode → `"diagram_relationships"`, package_id → `null`,
show_description → `false`. No migration to backfill.

### Bullet-shape rules

Deterministic ordering for stable diffs and exports.

**Default mode (`diagram_relationships`).** For each intra-diagram
relationship sorted by `(source.name, target.name, relationship_type)`,
emit two bullets in order: the source's name, then the target's name.
Non-deduplicated.

**Package mode (`package_elements`).** For each element in the package
sorted by `name`:

```
- {element.name}
```

**Both modes — `show_description=true` overlay.** Each bullet becomes
`- {element.name} ({element.description})`. If `description` is null
or empty, the parentheses are omitted for that single bullet
(`- {element.name}`).

**Header/footer.** H1 `# {diagram.name}` at top; H6
`###### (Dynamic list — auto-generated)` at the bottom.

### Edit-mode UX

The /view page's existing Edit/Save toolbar is enabled, but the
content textarea is hidden. Instead, a read-only preview of the
computed bullet list is shown alongside a "Source" panel with three
controls (top-to-bottom):

1. **Mode** — `<select>`: `Default (diagram relationships)` /
   `Package elements`.
2. **Package** — package picker, shown only when mode is
   `package_elements`, scoped to the current diagram's set.
3. **Show description** — checkbox; visible in both modes.

Save persists `data.dynamic_source` via `PUT /api/diagrams/{id}`.

### Read-only canvas mechanism

A synthesised `data.is_content_locked: true` flag is emitted on read
for any `dynamic_list` diagram. The flag is never stored. The
frontend hides the textarea and shows the Source panel when the flag
is truthy.

### No new MCP / CLI tools

`create_diagram` and `update_diagram` already accept arbitrary `data`
JSON. Setting `data.dynamic_source` is the same write path as setting
any other type's `data`. `scripts/check_surface_parity.py` therefore
requires no change.

## Why a new diagram_type under `markdown` rather than a new notation

- `markdown` already groups markdown-backed read surfaces (currently
  `text`). A new notation would be visual noise in the dialog without
  meaningful semantic separation.
- Export already special-cases `notation == "markdown"`; we want
  `dynamic_list` to ride that codepath unchanged.

## Why synthesise content on read rather than store it

- Storing snapshots would require an explicit "refresh" UX and goes
  stale silently when relationships or package membership change.
- Compute-on-read keeps the rendered markdown consistent with the
  underlying graph state with zero coordination cost.
- Export at time T reflects the state at time T (matches the issue's
  intent: "as displayed in browse mode").

## Why bullets are 2N for N intra-diagram relationships

User chose this explicitly during plan-time AskUserQuestion. Treats
each relationship endpoint as its own bullet (source, then target).
Deduplication can ship in a follow-up if the team revises the call.

## Why a read-only canvas with editable "Source" panel

- The content is auto-generated; allowing free text editing would
  fight with the next read.
- Mode/package/show_description still need user-driven choices, and
  the standard edit-mode chrome is the natural home for them.

## Consequences

- New migration `backend/app/migrations/m065_dynamic_list_diagram_type.py`.
- New service module `backend/app/diagrams/dynamic_list.py` with
  `compute_dynamic_list_content(db, diagram_id, *, mode, package_id,
  show_description) -> str`.
- New helper `list_intra_diagram_relationships(db, diagram_id)` in
  `backend/app/package_relationships/service.py` (the strict
  intra-diagram filter used by both the existing
  `GET /api/diagrams/{id}/relationships` element_relationships array
  and the new dynamic_list compute).
- `backend/app/diagrams/service.py::get_diagram` synthesises
  `data.content` + `data.is_content_locked = true` when
  `diagram_type == "dynamic_list"`.
- `frontend/src/lib/components/DiagramDialog.svelte` lists
  `dynamic_list` in the `markdown` notation's fallback array.
- New Svelte component `frontend/src/lib/canvas/text/DynamicListCanvas.svelte`
  renders the computed markdown via the existing markdown view, plus
  the Source panel.
- `frontend/src/routes/views/[id]/+page.svelte` branches on
  `data.is_content_locked` to render `<DynamicListCanvas>` instead of
  `<TextCanvas>`.
- CHANGELOG `[6.7.0]`.
- Diagram-type-count tests in `test_diagrams/test_registry.py` and
  `test_diagrams/test_new_diagram_types.py` bump from 18 → 19.

## Verification

- `pytest backend/tests/test_dynamic_list_compute.py` — full compute
  matrix (both modes, toggle on/off, null/empty descriptions).
- `pytest backend/tests/test_diagrams/test_dynamic_list_read.py` —
  read-time synthesis of `data.content` and `data.is_content_locked`.
- Export round-trip — `GET /api/export/diagram/{id}?format=md` on a
  dynamic_list diagram equals the API read's `data.content`.
- Playwright `tests/e2e/dynamic-list-diagram.spec.ts` — creation,
  browse, Edit toggle round-trip.
- `python scripts/check_surface_parity.py` passes unchanged.

## See also

- [ADR-187](ADR-187-Synthesised-Content-On-Read.md) — the
  compute-on-read pattern this ADR depends on.
- [ADR-137](ADR-137-Text-Diagram-Class.md) — sibling diagram type
  under the same `markdown` notation.
- [ADR-184](ADR-184-Element-Package-Membership.md) — `element.package_id`
  enables the package mode.
- [SPEC-186-A](specs/SPEC-186-A-Dynamic-List-Diagram-Type.md).
- Issue [#147](https://github.com/cgbarlow/iris/issues/147).
