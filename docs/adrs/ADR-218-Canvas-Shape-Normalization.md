# ADR-218: Canvas shape normalization for create_diagram

Status: Accepted (2026-05-28)

Builds on: [ADR-162](./ADR-162-Generic-MCP-Diagram-Creation-Workflow.md)
(generic `create_diagram` MCP workflow),
[ADR-094](./ADR-094-DoView-Notation-AI-Creation.md) /
[ADR-100](./ADR-100-DoView-Element-Backed-Nodes.md) (the
`apply_diagram_creation` path and its `_build_canvas_nodes` builder).

## WH(Y)

**In the context of** diagrams authored by MCP clients, where the shared
creation-format prompt (`backend/app/seed/creation_prompts.py`) teaches
models to emit the *flat* AI node shape
(`{id, type, label, position, size, visual}`) — the shape consumed by
`apply_diagram_creation` → `_build_canvas_nodes`, which converts it into
the Svelte-Flow *canvas* shape the frontend requires
(`{id, type, position, width, height, data: {label, entityType, ...}}`),

**facing** the fact that the generic `create_diagram` tool (ADR-162)
persists its `data` payload **verbatim** with no such conversion, so a
model that follows the creation prompt and then saves via
`create_diagram` stored nodes with no per-node `data` object — and the
frontend canvas crashed reading `n.data.entityType`
(`UnifiedCanvas.svelte` `fitViewOptions`), so the diagram "failed to
load" (issue [#238](https://github.com/cgbarlow/iris/issues/238)),

**we decided for** a single shape-detecting, idempotent normalizer
`normalize_canvas_data` (`backend/app/diagrams/canvas_normalize.py`)
applied at the **write** boundary (`create_diagram` + `update_diagram`)
so new saves are always canvas-shaped, and at the **read** boundary
(`get_diagram`) so legacy flat diagrams auto-heal on load without
touching storage; the existing `apply_diagram_creation` builder is
refactored to delegate its per-item conversion to the same authority
(protocols §13 DRY), a one-line frontend optional-chain guard is added
as defense-in-depth, and the three already-broken diagrams named in
issue #238 are repaired in place by a targeted, explicitly-scoped
script,

**and neglected** guarding only the frontend (turns the crash into a
blank canvas but leaves the data unrenderable and unfixed), rewriting
the creation prompt to emit canvas shape directly (brittle — relies on
every model transforming perfectly every time, and heals nothing
already stored), rejecting flat payloads in `create_diagram` (breaks
the documented MCP authoring flow), and a global startup data migration
that rewrites every diagram (would touch data the issue reporter
explicitly asked us to leave alone, and a nested-jsonb rewrite in
Postgres is error-prone),

**to achieve** MCP-authored diagrams that always render — regardless of
which save tool the model picks — plus immediate, zero-risk recovery of
every existing flat diagram on read, with the three reported diagrams
also physically repaired,

**accepting that** `create_diagram` now tolerates two input shapes
(flat and canvas) rather than one, that read-time normalization runs on
every diagram GET (a cheap shape check that is a no-op for
already-canvas data), and that the physical repair is a manual
out-of-band script run rather than an automatic migration.

## Decision

Add `backend/app/diagrams/canvas_normalize.py` as the single authority
for the flat → canvas transform:

- `flat_node_to_canvas(node, *, default_entity_type="")` — relocates
  `label` → `data.label`, `type` → `data.entityType`, `size` →
  top-level `width`/`height`, and non-empty `visual`/`description` into
  `data`; preserves unknown structural keys.
- `flat_edge_to_canvas(edge, *, default_relationship_type="")` — moves
  `type` → `data.relationshipType` (keeping the top-level `type` for
  renderer dispatch) and adds the `center` handles AI-authored edges use.
- `needs_normalization(data)` / `normalize_canvas_data(data)` —
  shape-detecting and idempotent: nodes/edges that already carry a dict
  `data` pass through untouched; non-canvas payloads (markdown
  `{content}`, sequence `{participants, ...}`) pass through untouched;
  input is never mutated.

Wiring:

- **Write:** `service.create_diagram` and `service.update_diagram`
  normalise `data` before persisting (so storage, notation detection,
  and thumbnails all see canvas shape).
- **Read:** `service.get_diagram` normalises the loaded `data` before
  returning (non-destructive auto-heal for legacy rows).
- **DRY:** `app/ai/creation.py::_build_canvas_nodes` /
  `_build_canvas_edges` delegate to `flat_node_to_canvas` /
  `flat_edge_to_canvas` (apply-path specifics — doview defaults, the
  phase-2 `_linkedDiagramIndex` stash — layered around the shared call).
- **Frontend:** `UnifiedCanvas.svelte` `fitViewOptions` filter
  optional-chains `n.data?.entityType` so a stray dataless node can
  never hard-crash the canvas on mount.
- **Repair:** `scripts/repair_flat_diagram_shape.py` rewrites every
  version of the EXPLICITLY-NAMED diagrams in place via the same
  normalizer and regenerates their thumbnails. It refuses to run without
  `--diagram-id` arguments and never scans all diagrams.

## Consequences

**Positive:**

- MCP-authored diagrams render whether saved via `apply_diagram_creation`
  or `create_diagram`.
- Every existing flat diagram renders the moment the fix deploys (read
  heal), with no data-rewrite risk.
- One transform authority, reused on write, read, the apply path, and
  the repair script.
- No new write endpoints → surface-parity (ADR-182, §14) unaffected.

**Negative / accepted trade-offs:**

- `create_diagram` accepts both flat and canvas input shapes.
- A cheap shape check runs on every diagram GET.
- The physical repair is a one-off operational script run, not an
  automatic migration (a deliberate choice to keep the blast radius to
  the three named diagrams).

## Rejected alternatives

- **Frontend guard only.** Stops the crash but renders dataless nodes
  (no label/type) and leaves the stored data broken.
- **Rewrite the creation prompt to emit canvas shape.** Pushes a fragile
  per-token transform onto every model on every run and heals nothing
  already persisted.
- **Reject flat payloads in `create_diagram`.** Breaks the documented
  ADR-162 authoring flow that the shared creation prompt teaches.
- **Global startup data migration.** Would rewrite diagrams the issue
  reporter asked us not to touch, and a nested-jsonb rewrite in Postgres
  is error-prone versus reusing the Python normalizer on the few named
  rows.

## References

- [SPEC-218-a — normalizer contract, wiring, repair scope, acceptance criteria](./specs/SPEC-218-a-Canvas-Shape-Normalization.md)
- Issue [#238](https://github.com/cgbarlow/iris/issues/238) — "diagram failed to load as generated by Iris MCP"
- [ADR-162](./ADR-162-Generic-MCP-Diagram-Creation-Workflow.md) — generic `create_diagram` workflow
- [ADR-094](./ADR-094-DoView-Notation-AI-Creation.md) — AI diagram creation / `_build_canvas_nodes`
- [ADR-182](./ADR-182-Surface-Parity-Discipline.md) — surface parity (unaffected: no new write endpoint)
