# SPEC-136-A: BPMN 2.0 notation

ADR: [ADR-136](../ADR-136-BPMN-Notation.md)

## Element catalogue (14 base types, OMG BPMN 2.0 §7.4)

| Category   | Entity type         | Discriminator(s) on `data`                                              |
|---|---|---|
| Activity   | `task`              | `taskType` ∈ {none, user, service, manual, send, receive, script, business_rule} + marker_* booleans (loop, multi_instance_parallel, multi_instance_sequential, compensation) |
| Activity   | `subprocess`        | `subprocessKind` ∈ {embedded, event, ad_hoc, transaction} + marker_*    |
| Activity   | `call_activity`     | (none — thick border)                                                   |
| Event      | `event_start`       | `eventTrigger` ∈ {none, message, timer, signal, conditional, error, escalation, compensation, link} |
| Event      | `event_intermediate`| `eventDirection` ∈ {catch, throw} + `eventTrigger` (subset by direction)|
| Event      | `event_end`         | `eventTrigger` ∈ {none, message, signal, error, escalation, compensation, terminate} |
| Event      | `event_boundary`    | `boundaryInterrupting` (bool) + `eventTrigger`                          |
| Gateway    | `gateway`           | `gatewayType` ∈ {exclusive, inclusive, parallel, event_based, complex, parallel_event_based} |
| Swimlane   | `pool`              | `orientation` ∈ {horizontal, vertical}                                  |
| Swimlane   | `lane`              | (parent must be a pool; enforced by validator rule 8)                   |
| Data       | `data_object`       | `dataKind` ∈ {object, input, output, collection}                        |
| Data       | `data_store`        | (none — cylinder)                                                       |
| Artifact   | `group`             | (none — dashed rounded rectangle)                                       |
| Artifact   | `text_annotation`   | (none — bracket marker)                                                 |

### Connecting object types

| Key                          | Render                                                      |
|---|---|
| `sequence_flow`              | Solid line, filled arrowhead                                |
| `sequence_flow_default`      | Solid line + diagonal slash near source                     |
| `sequence_flow_conditional`  | Solid line + small diamond near source                      |
| `message_flow`               | Dashed line, open arrowhead                                 |
| `association`                | Dotted line, no arrowhead (or open if directional)          |
| `data_association`           | Dotted line, open arrowhead                                 |

`association` is shared with UML — the active notation context
disambiguates the renderer in `DynamicEdge.svelte`.

## Diagram-type matrix (BPMN_DIAGRAM_TYPE_FILTER, ADR-082)

| Diagram type     | Allowed BPMN element keys                                                      |
|---|---|
| `process`        | All except `pool` (single-pool process is implicit)                            |
| `collaboration`  | `null` (every element permitted, including multiple pools + message flows)     |
| `choreography`   | `task`, `event_*`, `gateway` only                                              |
| `free_form`      | `null`                                                                         |

## Authoring UX (researched against the most-loved BPMN tools)

The full research synthesis lives in the planning notes; the below is
the implementation-side specification.

### Two surfaces (universal pattern across loved tools)

1. **`BpmnPalette.svelte`** — left sidebar, six accordion sections
   (Activities / Events / Gateways / Swimlanes / Data / Artifacts), one
   representative per family. Drag-and-drop emits the entity-type key
   via `application/iris-bpmn-entity` data transfer.
2. **`ContextPad.svelte`** — Svelte Flow `<NodeToolbar>` on the
   selected node with the canonical bpmn-js action order: Append Task
   → Append Gateway → Append End Event → Connect → Change (wrench,
   tooltip "Change element type (R)") → Delete. Wrench tooltip
   explicitly names the keyboard shortcut to fix bpmn-js's
   discoverability gap.

### Searchable command palette (the most-praised UX in the category)

`CommandPalette.svelte` binds three global keys:

- **`N`** — create-anything (drop element at cursor on canvas)
- **`A`** — append-anything (after the selected element)
- **`R`** — replace (morph the selected element to a different type)

Fuzzy match across the full BPMN catalogue. Arrow keys + Enter to
confirm, Escape to dismiss. Backdrop click also dismisses. Bound at
document level; ignores keypresses inside other inputs/textareas.

### 2D event matrix picker (Iris's strong opinion)

`EventMatrixPicker.svelte` displays a 6 × 10 grid (positions ×
triggers). Illegal cells are visually disabled with a hatch pattern.
Output: `{ entityType, eventTrigger, eventDirection?, boundaryInterrupting? }`
applied as the new node's data.

### Right-side property panel (universal)

`PropertyPanel.svelte` — always visible, refreshes on selection. Three
tabs: General / BPMN / Documentation. The BPMN tab exposes the
discriminator selects + the activity marker checkboxes. Modal
property dialogs are explicitly avoided — every loved BPMN tool moved
to an always-on side panel.

### Hybrid validation (Camunda's pattern)

`bpmnRules.ts` exports two functions:

- `canConnect({source, target, edgeType, nodes})` — draw-time
  prevention. Returns `{ allowed: false, reason, ruleId }` for blocked
  connections; the toast text is the `reason`.
- `validateBpmn(data)` — whole-diagram pass returning `BpmnProblem[]`
  with severity (`error | warning | info`) and `elementIds` for click-
  to-focus.

`ProblemsPanel.svelte` displays the live list bottom-docked with a
header showing severity counts. Each row is clickable and emits
`onfocus(elementIds)` so the canvas can scroll/zoom to the offender.

### Anti-pattern rules shipped in v5.1.0 (15)

| ID                               | Severity | Description                                              |
|---|---|---|
| `sequence_flow_crosses_pool`     | error    | Sequence flow crosses pool boundaries                    |
| `message_flow_within_pool`       | error    | Message flow stays within a single pool                  |
| `message_flow_invalid_endpoint`  | warning  | Message flow endpoint is not activity/event/pool         |
| `start_event_has_inflow`         | error    | Start event has incoming sequence flow                   |
| `end_event_has_outflow`          | error    | End event has outgoing sequence flow                     |
| `outflow_from_end_event`         | (block)  | Draw-time only                                           |
| `inflow_to_start_event`          | (block)  | Draw-time only                                           |
| `start_event_no_outflow`         | warning  | Start event with zero outgoing flows                     |
| `end_event_no_inflow`            | warning  | End event with zero incoming flows                       |
| `missing_start_event`            | warning  | Process has activities but no start event                |
| `missing_end_event`              | warning  | Process has activities but no end event                  |
| `orphan_activity`                | warning  | Activity has no connections                              |
| `lane_outside_pool`              | error    | Lane not inside a pool                                   |
| `pointless_gateway`              | info     | Gateway with 1 in + 1 out                                |
| `unbalanced_gateways`            | info     | More diverging gateways than converging                  |
| `multiple_start_events`          | info     | More than one start event                                |
| `text_annotation_unlinked`       | info     | Text annotation without an Association                   |

### Anti-patterns we explicitly avoid (from research)

- Flat-listing every BPMN variant on the palette (draw.io's failure mode).
- Wrench-only morphing without keyboard shortcut or tooltip.
- Auto-opening the morph popup after every drop.
- Modal property dialogs.
- Top-down-only flow (default LTR; pools auto-orient).
- Promising mobile/touch authoring — read-only viewer + tap-to-comment only.
- Bizagi-style "click Validate" gating — we ship hybrid validation instead.

## Theme defaults (Camunda-inspired neutral palette)

Seeded by `m043_bpmn_notation.py` (SQLite) and `m044_bpmn_notation.sql`
(Supabase) into the `themes` table as `bpmn-default`.

- Tasks / Subprocesses / Activities: white fill, `#202931` border.
- Call Activity: 4px border (visual cue for "calls another process").
- Start Events: pale green fill, green border, 1px stroke.
- Intermediate Events: pale grey fill, amber border, double 1px concentric circles.
- End Events: pale red fill, red border, 4px stroke.
- Boundary Events: dashed concentric circles when `boundaryInterrupting=false`.
- Gateways: white diamond, amber border, 2px stroke.
- Pools / Lanes: white fill, `#202931` border (lanes 1px, pools 2px).
- Data: white fill, dark border.
- Group: transparent dashed rounded rectangle.
- Text Annotation: bracketed label, transparent.
- Sequence Flow / Message Flow: 2px dark stroke (`#202931`); message flows dashed.
- Association / Data Association: 1px medium grey, dotted.

Border radius defaults to `6px` on activities (rounded BPMN convention).

## AI creation prompts

Seeded by `m043_bpmn_notation.py` and `m044_bpmn_notation.sql` into
`ai_creation_prompts`:

- `bpmn-notation` (layer = `notation`): structural rules, element
  catalogue, hard rules (no sequence flows across pools, every process
  starts with a start event, lanes inside pools), discriminator
  conventions.
- `bpmn-process` (layer = `diagram_type`): single-participant guidance,
  lanes for responsibilities, LTR or TTB but not both.
- `bpmn-collaboration` (layer = `diagram_type`): multi-pool guidance,
  message flows across pool boundaries, black-box pools.
- `bpmn-choreography` (layer = `diagram_type`): two-participant per
  task, no controlling pool.

## MCP / public API exposure

The MCP `ask` tool (`mcp/src/iris_mcp/tools.py:~304`) already accepts
a freeform `notation` parameter validated server-side against the
registry. With BPMN seeded, MCP exposure is automatic — no MCP code
change. A regression test confirms `notation: "bpmn"` is accepted.

## Performance budget

`BpmnPerformance` test asserts a 500-node process renders within an
agreed budget (initial render < 500 ms; pan/zoom maintains 30+ fps via
Svelte Flow's built-in viewport culling). This explicit guard exists
to prevent the Bizagi failure mode ("12-tab files take 5+ minutes to
open") that recurred in user reviews.

## Files

| Surface                | File                                                                                          |
|---|---|
| Type system            | `frontend/src/lib/types/canvas.ts` (BpmnEntityType, BpmnCategory, BPMN_ENTITY_TYPES, BPMN_RELATIONSHIP_TYPES, BPMN_DIAGRAM_TYPE_FILTER, BPMN_DEFAULT_DISCRIMINATORS) |
| Backend detection      | `backend/app/diagrams/notation_detection.py` (BPMN_TYPES + branch)                            |
| SQLite registry seed   | `backend/app/migrations/m043_bpmn_notation.py` (notation, diagram_types, mappings, theme, AI) |
| Supabase registry seed | `backend/app/migrations/supabase/m044_bpmn_notation.sql`                                      |
| Node renderer          | `frontend/src/lib/canvas/renderers/BpmnRenderer.svelte`                                       |
| Edge renderer          | `frontend/src/lib/canvas/renderers/BpmnEdgeRenderer.svelte`                                   |
| Canvas dispatch        | `frontend/src/lib/canvas/DynamicNode.svelte`, `DynamicEdge.svelte`, `registry.ts`             |
| Create dialog fallback | `frontend/src/lib/components/DiagramDialog.svelte` (NOTATION_TYPE_FALLBACK)                   |
| Palette                | `frontend/src/lib/canvas/palette/BpmnPalette.svelte`                                          |
| Context pad            | `frontend/src/lib/canvas/palette/ContextPad.svelte`                                           |
| Command palette        | `frontend/src/lib/canvas/palette/CommandPalette.svelte`                                       |
| Event matrix picker    | `frontend/src/lib/canvas/palette/EventMatrixPicker.svelte`                                    |
| Property panel         | `frontend/src/lib/canvas/properties/PropertyPanel.svelte`                                     |
| Validation rules       | `frontend/src/lib/canvas/validation/bpmnRules.ts`                                             |
| Problems panel         | `frontend/src/lib/canvas/validation/ProblemsPanel.svelte`                                     |
| Backend tests          | `backend/tests/test_diagrams/test_bpmn_notation.py` (26 tests)                                |
| Frontend tests         | `frontend/tests/unit/bpmnEntityTypes.test.ts`, `bpmnValidation.test.ts` (26 tests)            |

## Amendment 2026-05-05 — `NotationPills` is the single source of truth (issue #27)

`NotationPills.svelte` previously hard-coded the visible notations and
silently omitted BPMN (and Markdown). Despite the registry, renderer,
palette, AI seed and DiagramDialog fallback all being wired up, the
user could not pick BPMN when creating a new view.

### Surface change

- `frontend/src/lib/components/NotationPills.svelte` now lists all
  seven notations: Simple, UML, ArchiMate, C4, **BPMN**, DoView,
  **Markdown**. The pill list is the canonical source for which
  notations a user can pick.
- A new optional `notations: string[]` prop scopes the visible pills
  for callers that need to exclude entries.
  `EntityDialog.svelte` passes `[..., excluding 'markdown']` because
  text views have no entities to add.
- The notation filter dropdown on the Views index
  (`frontend/src/routes/views/+page.svelte`) gains the same two
  missing entries (BPMN, Markdown).
- The diagram-type filter on the Views index gains entries for
  `collaboration`, `choreography` and `text` so BPMN- and Markdown-
  authored views are filterable.

### Verification

`frontend/tests/unit/notationPillsCoverage.test.ts` (added) reads
`NotationPills.svelte` and `DiagramDialog.svelte` and asserts that
every notation key registered in `NOTATION_TYPE_FALLBACK` appears in
the pill list. This catches the exact regression that produced
issue #27 — adding a notation to the registry without surfacing it in
the picker.

## Amendment 2026-05-05 — BPMN canvas UX integration map (issue #37, v5.2.0)

Per the ADR-136 v5.2.0 amendment, the six BPMN UX surfaces are now
mounted into the canvas via a new `BpmnAuthoringShell` wrapper. This
table is the surface-by-surface integration record — file paths,
state read/written, callback wiring.

### Integration map

| Surface | Mounts in | Reads | Writes (callback) | Notes |
|---|---|---|---|---|
| `BpmnPalette` | `BpmnAuthoringShell` left aside (220px) | `initialOpen` (default `'activity'`) | `onselect(key)` → shell creates a node via `makeBpmnNode(key)` at `findOpenPosition()` | Drag-start emits `application/iris-bpmn-entity` on `dataTransfer`; drop is handled by UnifiedCanvas. |
| `ContextPad` | Inside `BpmnRenderer` when `selected` | `nodeId` (renderer prop), `visible` (= `selected`) | `onaction(action, nodeId)` → bridged via `getContext('bpmnContextPadAction')` to the shell's `handleContextPadAction` | Wraps `<NodeToolbar position={Position.Right} offset={8}>` — auto-anchors to the node and follows pan/zoom. |
| `CommandPalette` | `BpmnAuthoringShell` page-level modal | `open` + `mode` (bound by shell), `bindShortcuts={false}` | `onpick(entry, mode)` → shell handles `create` / `append` / `replace` (replace mutates the existing node's `type` + `data.entityType` + `data.data` to the new BPMN_DEFAULT_DISCRIMINATORS) | Self-binding disabled because the same instance serves all three modes; the shell drives `mode` from N / A / R hotkeys. |
| `EventMatrixPicker` | `BpmnAuthoringShell` page-level modal | `open` (bound by shell) | `onpick(variant)` → shell creates an event node populated with `eventTrigger` + (maybe) `eventDirection` + (maybe) `boundaryInterrupting` | Opens automatically when an `event_*` entity is created via palette/drop/command; uses `pendingDropPosition` to remember the click site. |
| `PropertyPanel` | `BpmnAuthoringShell` right aside (280px) | `selection: PropertyPanelData \| null` derived from `selectedEditNodeId` + `canvasNodes` | `onchange(id, patch)` → shell maps `label` / `description` to top-level `data` and the rest to inner `data.data` (discriminators) | Always mounted for BPMN views (not gated on selection); shows an empty state when nothing's selected. Replaces the existing `ElementEditPanel` / `NodeStylePanel` / `LinkedDiagramPanel` stack for BPMN only. |
| `ProblemsPanel` | `BpmnAuthoringShell` bottom dock (80–200px) | `data: BpmnDiagramData` derived from `canvasNodes` + `canvasEdges` | `onfocus(elementIds[])` → shell sets `selectedEditNodeId` to the first id (canvas highlights via existing selection wiring) | Re-runs `validateBpmn(data)` reactively whenever nodes/edges mutate. |
| `BpmnToast` (new) | `BpmnAuthoringShell` fixed-position bottom-centre | `message` (bound by shell) | Self-clears after 3.5s; bindable so the shell can also clear/refresh | Surface for `canConnect` rejection reasons. ~50 lines, single-purpose, no new dep. |

### UnifiedCanvas hook props

| Prop | Type | Wired by | Used for |
|---|---|---|---|
| `onbeforeconnect` | `(c: Edge \| Connection) => boolean` | Shell's `handleBeforeConnect` | `<SvelteFlow isValidConnection={onbeforeconnect}>` — blocks the edge at draw-time when `canConnect` returns `{allowed: false}` and surfaces the reason via toast. |
| `ondropentity` | `(key: string, pos: { x: number; y: number }) => void` | Shell's `handleDropEntity` | Receives the palette drop after `useSvelteFlow().screenToFlowPosition` converts the cursor. Shell creates a BPMN node at the projected position. |
| `oncontextpadaction` | `(action: string, nodeId: string) => void` | Shell's `handleContextPadAction` | `setContext('bpmnContextPadAction', oncontextpadaction)` — BpmnRenderer's `<ContextPad onaction={…}>` calls back via this Svelte context. |

### BpmnRenderer additions

- New `id?: string` prop (xyflow auto-passes node ids to custom node components — only Iris's renderer interface didn't declare it).
- `import ContextPad from '$lib/canvas/palette/ContextPad.svelte'`.
- `const onContextPadAction = getContext<(action, nodeId) => void>('bpmnContextPadAction')`.
- Mount: `<ContextPad nodeId={id} visible={selected} onaction={(a, n) => onContextPadAction?.(a, n)} />` placed alongside the `<Handle>` elements at the top of the renderer template — visible only when `selected`, anchored by the inner `<NodeToolbar>`.

### Layout decisions

- `SvelteFlowProvider` wraps UnifiedCanvas's whole template so the script-level `useSvelteFlow()` call has a store to read.
- `BpmnAuthoringShell` is a CSS-grid 3-column layout (220px / 1fr / 280px) with a flex-row + bottom problems dock. `height: calc(100vh - 230px)` to match the existing canvas-area sizing.
- Hotkeys (N / A / R) are gated by `notation === 'bpmn'` and standard input-target guards (`INPUT` / `TEXTAREA` / `isContentEditable`).

### Files added in v5.2.0

| File | Lines | Purpose |
|---|---|---|
| `frontend/src/lib/canvas/bpmn/BpmnAuthoringShell.svelte` | ~430 | The shell itself. |
| `frontend/src/lib/canvas/bpmn/BpmnToast.svelte` | ~80 | The fixed-position toast. |
| `frontend/tests/unit/bpmnCanvasIntegration.test.ts` | ~135 | Static-parser regression guard (16 tests). |

### Files modified in v5.2.0

| File | Change |
|---|---|
| `frontend/src/lib/canvas/UnifiedCanvas.svelte` | Wrapped in `<SvelteFlowProvider>`; added 3 hook props (`onbeforeconnect`, `ondropentity`, `oncontextpadaction`); wired `isValidConnection` + `ondrop`/`ondragover`; `setContext('bpmnContextPadAction', …)`. |
| `frontend/src/lib/canvas/renderers/BpmnRenderer.svelte` | Added `id?: string` prop; mounts `<ContextPad>` when selected; reads action handler from `getContext('bpmnContextPadAction')`. |
| `frontend/src/routes/views/[id]/+page.svelte` | New `{:else if notation === 'bpmn'}` branch in the editing canvas-area chain that mounts `<BpmnAuthoringShell>` instead of the generic UnifiedCanvas + right-panel layout. |
| `docs/adrs/ADR-136-BPMN-Notation.md` | Amendment with integration decisions. |
| `docs/adrs/specs/SPEC-136-A-BPMN-Notation.md` | This integration map. |
| `CHANGELOG.md` | New `[5.2.0]` section. |
| `frontend/package.json` + `package-lock.json` | Version bump 5.1.2 → 5.2.0. |

## v5.4.1 amendment — issue #46 fixes

| Change | File | Notes |
|---|---|---|
| **Default edge type for BPMN** | `frontend/src/lib/canvas/UnifiedCanvas.svelte` | `defaultEdgeType` $derived gains a leading `notation === 'bpmn' ? 'sequence_flow'` arm. Without this, handle-drag connections in BPMN views landed as type `'uses'` and `validateBpmn::no_outgoing_sequence_flow` kept firing. |
| **Connect → Relationship** | `frontend/src/lib/canvas/bpmn/BpmnAuthoringShell.svelte` | New async `handleBpmnConnect(srcId, tgtId)` wired as `onconnectnodes` on `<UnifiedCanvas>`. Resolves source/target entityIds; if both present, POSTs `/api/relationships` with `relationship_type: 'sequence_flow'`; always pushes a new edge with `type: 'sequence_flow'` to `canvasEdges`; calls `dirty()`. Mirrors the page-level `handleRelationshipSave` flow other notations use. |
| **Problems panel `flex-shrink: 0`** | `frontend/src/lib/canvas/bpmn/BpmnAuthoringShell.svelte` (.bpmn-shell__problems) | Pre-fix the `max-height: 200px` cap was honoured visually but the flex algorithm still expanded the panel; adding `flex-shrink: 0` makes the cap stick. |
| **Event trigger flyout** | `frontend/src/lib/canvas/palette/EventTriggerFlyout.svelte` (new), `frontend/src/lib/canvas/palette/bpmnEventModel.ts` (new) | Compact ContextPad-style horizontal row of trigger glyph buttons. Replaces the 60-cell EventMatrixPicker dialog on palette-drop / palette-click. Filters `TRIGGERS` by `isLegal(position, trigger)` so only legal triggers render. `bpmnEventModel.ts` is the shared source for `TRIGGERS`, `isLegal`, `variantFor`, and a new `positionFor(entityType)` helper. |
| **EventMatrixPicker no longer auto-opens on palette flow** | `frontend/src/lib/canvas/bpmn/BpmnAuthoringShell.svelte` (`createNode`) | The matrix dialog stays mounted for the Ctrl-N command-palette advanced create flow; on the palette path the placed node gets a default `none` trigger and the `EventTriggerFlyout` shows next to it. |
| **createBpmnElement console.error** | `frontend/src/lib/canvas/bpmn/BpmnAuthoringShell.svelte` (createBpmnElement catch) | In addition to the `toastMessage`, emit a `console.error` so silent ContextPad failures are diagnosable in production. |
| **Trio Add Element button gated on notation !== 'bpmn'** | `frontend/src/routes/views/[id]/+page.svelte` (canvas toolbar Create group) | The BPMN palette sidebar already covers element creation; the trio's Add Element button is hidden on BPMN. Link Element + Add Diagram remain. |
| **Trio duplicates removed** | `frontend/src/routes/views/[id]/+page.svelte` (Text + BPMN inner branches) | v5.4.0 added duplicate trios in the Text and BPMN inner branches. The parent canvas toolbar's trio already covers both. The duplicates have been removed; FocusView's intentional duplicate (when the focus overlay hides the parent) is preserved. |
