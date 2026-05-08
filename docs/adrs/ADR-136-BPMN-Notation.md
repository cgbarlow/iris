# ADR-136: BPMN 2.0 notation

Status: Accepted (2026-05-04) — amended 2026-05-05 (issues #27, #33, #37, #37-reopen) and 2026-05-06 (v5.4.0 BPMN-as-Elements + UI polish)

## Context

Iris ships five notations today (Simple, UML, ArchiMate, C4, DoView).
The notation registry, theme system, palette, AI creation prompts, and
canvas dispatch are all extension-friendly thanks to
[ADR-079](ADR-079-Diagram-Type-Notation-Registry.md),
[ADR-082](ADR-082-Diagram-Type-Element-Filtering.md), and
[ADR-094](ADR-094-DoView-Notation-AI-Creation.md). DoView demonstrated
the cleanest end-to-end pattern: a registry seed + a notation-specific
renderer + an entry on the `data` field for variant discriminators + a
layered AI prompt.

Issue #25 asked for **full BPMN 2.0** — not a subset — and to expose
it through every Iris surface (canvas, palette, MCP, AI). Users
explicitly wanted elements **grouped like ArchiMate Layers** so the
catalogue stays discoverable.

We did UX research across the most-loved BPMN tools (bpmn-js / Camunda
Modeler ~9.5k★, Bizagi G2 4.6/290, Lucidchart G2 4.5/6000) before
designing the authoring experience. The findings are in
[SPEC-136-A](specs/SPEC-136-A-BPMN-Notation.md).

## Decision

Add **BPMN 2.0 as the sixth notation** following the DoView extension
pattern. Specifically:

1. **Element model**: 14 base entity types covering every BPMN 2.0
   §7.4 category. Variants (User Task, Service Task, Timer Event,
   etc.) are selected through **discriminator fields on `data`**
   (`taskType`, `gatewayType`, `eventTrigger`, `eventDirection`,
   `boundaryInterrupting`, `subprocessKind`, `dataKind`) rather than as
   ~80 separate type keys. The renderer reads the discriminators to
   draw the right inner marker. This keeps the registry tight while
   covering the full BPMN 2.0 element set.

2. **Category grouping** mirrors the BPMN 2.0 spec §7.4 categories
   (Activities / Events / Gateways / Connecting Objects / Swimlanes /
   Data / Artifacts) using a `category: BpmnCategory` field on each
   entity-type info — analogous to how ArchiMate uses `layer`.

3. **Diagram types**: reuse the existing `process` slot from m020
   (BPMN as a non-default option, preserving any existing process
   diagrams). Add `collaboration` and `choreography` as BPMN-default
   diagram types.

4. **Authoring UX** picks proven patterns from the most-loved BPMN
   tools and one strong-opinion improvement (the 2D event matrix
   picker — no surveyed tool gets this right). Full UX spec in
   SPEC-136-A.

5. **Validation** ships as 15 hand-curated rules (the well-known BPMN
   anti-patterns) running both at draw time (silent prevention with a
   1-line toast) and persistently (Problems panel with click-to-focus).
   Hybrid prevention + listing model — the Camunda Modeler approach.

6. **Theme defaults**: a Camunda-inspired neutral palette so BPMN
   diagrams look familiar to anyone who has used bpmn-js.

7. **AI creation prompts**: one notation-level prompt teaching BPMN
   structural rules + three diagram-type prompts (process /
   collaboration / choreography). The MCP `ask` tool gains BPMN
   support automatically — it already accepts any registered notation.

## Why discriminator fields, not 80 explicit entity types

BPMN events alone have ~50 legal variants (5 positions × ~10
triggers, minus illegal combinations). Listing every variant as its
own entity type would:

- Bloat the registry to ~80 entries — ArchiMate's full layer set is
  comparable, and it's already on the larger end of the catalogues.
- Force the palette to either flat-list everything (draw.io's
  documented failure mode — unscannable) or hide variants behind a
  matrix picker anyway.
- Bloat detection logic, theme keys, and AI prompts proportionally.

Keeping 14 base types and putting the variant axis on `data` mirrors
how the OMG BPMN spec itself models events (`(EventDefinition,
EventType)`). The matrix picker exposes the full 2D space with no
loss of expressivity.

## Why a 2D event matrix picker

None of the surveyed tools (bpmn-js, Camunda Modeler, Bizagi,
Lucidchart, Visual Paradigm, draw.io) present events as the 2D space
they actually are — they hide variants behind wrenches, popups, or
flat-listed shapes. Users repeatedly ask in the bpmn.io forum for a
clearer affordance.

The matrix is small (6 rows × 10 columns = 60 cells) and direct.
Disabled cells visualise the legal/illegal combinations from the BPMN
2.0 spec, which is itself a teaching moment for first-time BPMN users.

## Why hybrid validation

Bizagi's "click Validate" model is universally complained about —
errors slip through to export. bpmn-js's silent prevention is loved
but invisible (only a cursor cue) so users don't learn the rule.
Camunda's hybrid (block at draw time + persistent badge + Problems
panel) is best of both. We adopt it directly.

The 15-rule starter set is hand-curated rather than imported from
bpmnlint to keep the dependency surface small. We can swap in
bpmnlint later if it earns its keep.

## Why not full bpmn-io interop (XML import/export)

BPMN 2.0 XML is its own substantial body of work. Iris's storage
model is the diagram JSON; round-tripping to/from BPMN XML is a
worthwhile follow-up but not in scope for v5.1.0. Current users want
to author BPMN models *in Iris*, not necessarily import from
Camunda's modeller. Defer to a separate ADR when the demand arrives.

## Why deprecate nothing

This addition is pure extension. The existing `process` diagram type
keeps its current default notation — BPMN is offered as an
alternative for it. No migrations renumber, no existing diagrams are
touched.

## Compatibility

- Existing diagrams unaffected — BPMN is opt-in per diagram.
- The MCP `ask` tool gains BPMN as an accepted notation parameter
  with no MCP-side code change (server-side validation queries the
  registry).
- Element auto-detection (`backend/app/diagrams/notation_detection.py`)
  recognises BPMN base types; mixed-notation diagrams report multiple
  notations as before.

## Out of scope (deferred to follow-up issues)

- **Shape-pinned comment threads** (Lucidchart's strongest
  differentiator, identified during research) — notation-agnostic;
  belongs in its own issue against `CommentsPanel`.
- **Element templates** (Camunda-style "Send Slack Message" pre-
  configured Service Tasks) — needs its own template registry design.
- **bpmnlint integration** for the Problems panel — start with the
  hand-curated 15 rules; integrate the upstream linter later if it
  earns its keep.
- **BPMN XML import/export** — its own substantial workstream.
- **Pool/Lane swimlane container semantics** — Svelte Flow's
  parent/child model needs more validation on touch/keyboard
  reordering. Pools/lanes ship as styled rectangles in v5.1.0; full
  container semantics in a follow-up.

## See also

- [ADR-079](ADR-079-Diagram-Type-Notation-Registry.md) — registry.
- [ADR-082](ADR-082-Diagram-Type-Element-Filtering.md) — element
  filtering by diagram type.
- [ADR-094](ADR-094-DoView-Notation-AI-Creation.md) — pattern
  template followed by this ADR.
- [SPEC-136-A](specs/SPEC-136-A-BPMN-Notation.md) — element
  catalogue, theme, validation rules, and full UX spec.

## Amendment 2026-05-05 — surface BPMN in Create dialog (issue #27)

UAT noted that BPMN was nowhere to be found in the Create dialog —
"I did not see BPMN notation listed when creating a new diagram/view,
not sure how to create BPMN artefacts."

The cause was that the v5.1.0 work updated the registry, the renderer,
the palette, the MCP, the AI seed, and the `DiagramDialog` fallback
type list — but missed the **`NotationPills` component itself**, which
hard-coded a five-entry list (Simple, UML, ArchiMate, C4, DoView).
DoView shipped fine because it happened to be in that list; BPMN
silently fell off the picker.

**Decision:** make `NotationPills` the single source of truth for
which notations are user-pickable, listing all seven (Simple, UML,
ArchiMate, C4, **BPMN**, DoView, Markdown). Callers can still scope
the visible pills via an optional `notations` prop — `EntityDialog`
uses this to exclude `markdown`, since text views have no entities to
add.

The Views index notation filter dropdown gained the same two missing
entries (BPMN, Markdown) for consistency.

This is a one-line root cause that would have been caught earlier by
a test asserting "every registered notation is rendered in
NotationPills". A unit test against the registry vs. the pill list now
exists to prevent regression.

## Amendment 2026-05-05 — EntityDialog BPMN case (issue #33, v5.1.2)

UAT against v5.1.1 surfaced the *next* link in the same chain: the
NotationPills picker now offers BPMN (per the previous amendment), but
clicking **Add Element** on a BPMN view opened `EntityDialog` and
showed Simple-notation entity types (Actor, Boundary, Component, Note,
Service, …) — because `EntityDialog.svelte`'s entity-type switch had
no `case 'bpmn':` and silently fell through to the `default:` Simple
branch.

Fix in v5.1.2: add a `case 'bpmn':` branch that uses
`BPMN_ENTITY_TYPES` and applies `BPMN_DIAGRAM_TYPE_FILTER`, mirroring
the UML / DoView pattern in the same file. A new coverage test
`entityDialogBpmn.test.ts` asserts that **every notation key in
`NotationPills.ALL_NOTATIONS`** has a corresponding switch case in
`EntityDialog` (markdown excepted — text views have no entities;
simple is the `default:` fallback by convention). This catches the
exact regression class — adding a notation to the pills without
wiring its entity types in the dialog.

This is the same v5.1.0 oversight pattern as the v5.1.1 NotationPills
fix: the registry, renderer, themes, palette and validation rules
shipped, but the picker dialog was not updated. The two coverage
tests (notation-pills + entity-dialog) together close that loop.

The deeper UX gap — the BPMN authoring surfaces (`BpmnPalette` /
`ContextPad` / `CommandPalette` / `EventMatrixPicker` /
`PropertyPanel` / `ProblemsPanel`) that exist on disk but are not
mounted into the canvas — is tracked separately for v5.2.0
(see issue #34). v5.1.2 is the last v5.1.x patch.

## Amendment 2026-05-05 — UX surface integration (issue #37, v5.2.0)

The six BPMN authoring surfaces designed in this ADR (palette, context
pad, command palette, event matrix picker, property panel, problems
panel) were built as standalone components in v5.1.0 but never wired
into the canvas. Confirmed pre-v5.2.0 by `grep -rn 'BpmnPalette|
ContextPad|CommandPalette|EventMatrixPicker|PropertyPanel|
ProblemsPanel' src/routes/ src/lib/canvas/UnifiedCanvas.svelte`
returning zero hits.

This amendment records the **integration decisions** — no new design,
just how the existing components plug into the existing canvas.

### Where each surface mounts

| Surface | Mount site | Why there |
|---|---|---|
| `BpmnPalette` | New `BpmnAuthoringShell` left column | Self-contained 220px aside; sits next to UnifiedCanvas. |
| `ContextPad` | Inside `BpmnRenderer` when `selected` | Already wraps `<NodeToolbar>`, which auto-anchors via xyflow's per-node context. Placing it in the renderer is the only way it can read that context. |
| `CommandPalette` | Page-level modal mounted by the shell | Modal dialog (top: 20%); needs its `open`/`mode` driven externally so the same instance handles N (create), A (append) and R (replace). |
| `EventMatrixPicker` | Page-level modal mounted by the shell | Same shape as CommandPalette; opened either by the create flow on `event_*` keys or the context-pad/command-palette replace flow. |
| `PropertyPanel` | New `BpmnAuthoringShell` right column | Always-on per spec; replaces the conditional `ElementEditPanel` / `NodeStylePanel` / `LinkedDiagramPanel` stack for BPMN views only. |
| `ProblemsPanel` | New `BpmnAuthoringShell` bottom dock | Below the canvas; reactive to `validateBpmn(data)` so it updates as nodes/edges change. |

### Wiring decisions

1. **Action callback path for ContextPad** — the shell sets a Svelte
   context value `bpmnContextPadAction` (via UnifiedCanvas's
   `setContext`). BpmnRenderer reads it with `getContext`. Avoids
   prop-drilling through UnifiedCanvas → DynamicNode → BpmnRenderer
   for a callback only one renderer needs.
2. **canConnect surfacing** — wired through xyflow's
   `isValidConnection` prop on `<SvelteFlow>`. The shell's handler
   maps the verdict's `reason` into a fixed-position toast
   (`BpmnToast`) so the user sees *why* a connection was blocked.
3. **Drag-drop from palette** — `BpmnPalette` already emits
   `application/iris-bpmn-entity` on drag start. UnifiedCanvas
   adds `ondrop` + `ondragover` handlers on its outer div, uses
   `useSvelteFlow().screenToFlowPosition` to convert the cursor
   coordinate into flow coordinates, and emits `ondropentity(key,
   pos)`. The shell makes a node from that.
4. **N / A / R hotkeys** — moved out of `CommandPalette`'s self-
   binding (`bindShortcuts={false}`) and lifted into a
   `<svelte:window onkeydown>` inside the shell. Reason: the palette
   is mounted globally on every BPMN view, but the hotkeys must NOT
   fire on non-BPMN views. The shell-level handler also gates them on
   `notation === 'bpmn'`.
5. **Toast** — new `BpmnToast` component (~50 lines, no library —
   single consumer). Two-way bindable `message` prop; auto-clears.
6. **SvelteFlowProvider wrap** — required to use `useSvelteFlow()` at
   the UnifiedCanvas script level (above the `<SvelteFlow>` instance)
   so the drop handler has access to `screenToFlowPosition`. The
   provider wraps the whole template and is benign for non-drop usage.

### Why a new shell component instead of inlining into the views detail page

The detail page is already 3.2k lines after the v5.1.x renames. The
3-column layout + 6 surface mounts + hotkey relay + drop handling
would add ~350 more lines across an already-busy file. A shared
`BpmnAuthoringShell.svelte` keeps the BPMN concern in one file and
reduces the page-level surgery to a single `{:else if notation ===
'bpmn'}` branch — easier to review, easier to remove if BPMN ever gets
extracted into its own route.

### Regression guard

`frontend/tests/unit/bpmnCanvasIntegration.test.ts` (16 tests)
asserts: shell file exists, shell imports the five direct surfaces
plus `BpmnToast`, shell mounts each one, the page imports + mounts
the shell behind the BPMN guard, UnifiedCanvas declares the three new
hook props and wires them, and BpmnRenderer mounts ContextPad and
reads the context handler. Same static-parser style as the v5.1.1 /
v5.1.2 coverage tests.

## Amendment 2026-05-05 — v5.3.1 hot-fix (issue #37 reopen)

UAT against v5.2.0 / v5.3.0 surfaced a critical regression: every
canvas — not just BPMN — crashed on load with

> Uncaught Error: To call useStore outside of `<SvelteFlow />` you
> need to wrap your component in a `<SvelteFlowProvider />`

### Root cause

v5.2.0 added `useSvelteFlow()` at the script level of
`UnifiedCanvas` to power the BPMN palette drag-drop's coordinate
projection (`flow.screenToFlowPosition`). xyflow's hook reads
context via `getContext` AT CALL TIME. v5.2.0 *also* wrapped
UnifiedCanvas's own template in `<SvelteFlowProvider>` to satisfy
the hook — but Svelte's component lifecycle runs the script BEFORE
the template mounts. So the hook ran with no provider above it and
threw on every canvas mount, regardless of notation. Caught only in
runtime UAT, not in `svelte-check` (which doesn't execute the hook).

### Fix

Extract a thin `CanvasDropArea` component (`src/lib/canvas/CanvasDropArea.svelte`)
that owns the drop handlers AND calls `useSvelteFlow()` from its own
script. Mount it inside the existing `<SvelteFlowProvider>` so its
initialisation runs AFTER the provider sets up:

```
<SvelteFlowProvider>
  <CanvasDropArea ondropentity={…}>
    <div class="model-canvas">
      <SvelteFlow ... />
    </div>
  </CanvasDropArea>
</SvelteFlowProvider>
```

CanvasDropArea uses `display: contents` on its wrapper so the
existing canvas layout is unchanged.

### Regression guard

`bpmnCanvasIntegration.test.ts` adds:

```ts
it('UnifiedCanvas does NOT call useSvelteFlow at script level (v5.3.1 regression guard)', () => {
  expect(src).not.toMatch(/^\s*const\s+\w+\s*=\s*useSvelteFlow/m);
  expect(src).not.toMatch(/import[\s\S]*?useSvelteFlow[\s\S]*?from\s+['"]@xyflow\/svelte['"]/);
});
```

Catches exactly the v5.2.0 mistake — calling the hook from
UnifiedCanvas's script (where the provider in the same template
isn't yet mounted). Future drop-handler / flow-coord code must live
in a child of `<SvelteFlowProvider>` or use `CanvasDropArea` as the
established pattern.

### Why this wasn't caught earlier

- `svelte-check`: runs the type system, not the runtime; the hook's
  return type is correct so type-check passed.
- The vitest integration test in v5.2.0 was static-parser style,
  asserting `useSvelteFlow` was *called* but not in what context.
  v5.3.1 tightens the assertion to *forbid* the call at script level
  in UnifiedCanvas — the right shape of regression guard.

## Amendment 2026-05-06 — BPMN-as-Elements alignment + UI polish (v5.4.0)

UAT against v5.3.x surfaced an architectural divergence and seven UI
issues against the BPMN authoring shell. The headline decision is
**BPMN nodes are now Iris Elements** (matching every other notation):
adding a Task / Event / Gateway etc. POSTs `/api/elements` first and
stores `entityId` on the canvas node. BPMN content joins the rest of
the platform — search, knowledge graph, tags, comments, versioning,
and `iris://element/<id>` references all start working.

### A. BPMN-as-Elements (architectural)

Pre-v5.4 every other notation's `handleAddElement` POSTed
`/api/elements` and stored the resulting Element id on the canvas
node. BPMN was the outlier — `BpmnAuthoringShell::makeBpmnNode`
generated a node with no `entityId`, so BPMN content was invisible to
search/graph/tagging/etc.

Fix: a new `createBpmnElement(entityKey, name)` helper in the shell.
All four node-creation paths route through it — drag-from-palette,
drop-on-canvas, CommandPalette `create`/`append`, ContextPad-append,
and the EventMatrixPicker create flow. `replace` mode in
`handleCmdPick` PUTs `/api/elements/<id>` to update the existing
Element's `element_type` rather than creating a new one. PropertyPanel
edits (label/description) call `updateBpmnElement(entityId, patch)`
fire-and-forget so the Element row stays in sync with the canvas.

This is the architecturally correct shape — BPMN data lives in the
same place every other notation's data lives.

### B. Per-entity-type node sizing

Pre-v5.4 every BPMN node was created with `width: 200`. Visually:
- Events render as 56×56 circles (`.bpmn-event-wrap` CSS) — bounding
  box extended ~150px past the circle.
- Gateways same (56×56 diamonds).
- Data objects 48×64.
- Pools/lanes are large containers (240×120+).

The over-wide bounding box pushed `<NodeToolbar>` (ContextPad) far to
the right of the actual shape, making the action buttons feel
disconnected and giving the user the impression they were clicking
the connection-handle dots instead of pad buttons.

Fix: a `BPMN_NODE_DIMENSIONS` lookup with per-entity-type widths +
heights that match the renderer CSS. `makeBpmnNode` reads from it.
The page's BPMN-trio handlers (Add Element / Add Diagram, see §G)
duplicate the lookup as `bpmnDimsFor()` until a v5.5 refactor moves
the constant into `$lib/types/canvas.ts`.

### C. ContextPad bring-forward / send-backward

When pools and lanes stack, the user previously had no z-order
control. ContextPad gains two new actions (`bring_forward` ↑ /
`send_backward` ↓). Shell handler computes max/min `zIndex` of other
nodes and assigns +1/-1 — the optional `zIndex` field on xyflow's
`Node` type is honoured by SvelteFlow's renderer.

### D. Lane-on-pool parent detection

`validateBpmn::lane_outside_pool` walks `parentId` correctly, but
xyflow doesn't auto-set `parentId` when a lane is dragged onto a pool
visually. The `lane_outside_pool` error fired even when the user had
clearly dropped the lane inside the pool.

Fix: a new `onnodedragstop` prop on `<UnifiedCanvas>` forwarded to
xyflow. The shell's `handleBpmnDragStop` hit-tests the dragged lane's
centre against pool rectangles; on hit, `parentId` is set and the
error clears.

### E. ProblemsPanel scroll containment

`.bpmn-shell__problems` had `overflow: hidden` so the inner list's
`overflow-y: auto` was clipped. Long problem lists scrolled the
whole page instead of the panel. Fix: `overflow-y: auto` on the
wrapper.

### F. Theme-selector hidden on BPMN

Theme is fixed for BPMN by the m043 `bpmn-default` seed; the
ThemeSelector is irrelevant. Same on Text views (no canvas to
theme). Both are now gated.

### G. Add Element / Link Element / Add Diagram on BPMN

The trio toolbar previously rendered only on the canvas `{:else}`
branch — invisible on BPMN. Now rendered above `<BpmnAuthoringShell>`
when `notation === 'bpmn' && editing`. Page-level handlers branch on
`canvasType === 'bpmn'`:

- **Add Element** opens `EntityDialog` with notation pinned to BPMN.
  Result POSTs `/api/elements` and adds a canvas node with the right
  `BPMN_NODE_DIMENSIONS` and `BPMN_DEFAULT_DISCRIMINATORS` payload.
- **Link Element** opens `ElementPicker`. If a node is selected, sets
  `entityId` on it; if no node selected, surfaces a helpful error.
- **Add Diagram** opens `DiagramPicker`. Result places a `call_activity`
  BPMN node (BPMN-standard sub-process reference) with `linkedModelId`
  pointing at the picked diagram.

### Out of scope (deferred to v5.5+)

- Refactoring `BPMN_NODE_DIMENSIONS` + `BPMN_DEFAULT_DISCRIMINATORS`
  into `$lib/types/canvas.ts` so the page and shell share a single
  source. Both currently maintain the same lookup; mismatches would
  show up in tests.
- A bulk "select multiple → bring to front" action.
- Auto-detection of nested swimlanes (lane-in-lane).

## Amendment 2026-05-06 — v5.4.1 fixes (issue #46)

UAT against v5.4.0 surfaced four BPMN issues the v5.4.0 work didn't
catch and one UX redesign request. This amendment captures the
follow-up.

### A. BPMN edges create real Relationship records (issue #46 item #10)

Pre-fix, BPMN handle-drag connections only updated local
`canvasEdges` state — no `/api/relationships` record was created. So
`/elements/<id>`'s Relationships panel (which queries
`/api/relationships?element_id=…`) showed nothing for BPMN-drawn
connections, even though the Element itself existed via v5.4.0's
BPMN-as-Elements work.

`BpmnAuthoringShell` now wires `onconnectnodes={handleBpmnConnect}`
on `<UnifiedCanvas>`. The handler:

- Resolves source/target nodes from `canvasNodes`.
- If both have `data.entityId`, POSTs `/api/relationships` with
  `relationship_type: 'sequence_flow'`, capturing the resulting id.
- Adds an edge to `canvasEdges` with `type: 'sequence_flow'` and
  `data.relationshipId` if the POST succeeded.
- Calls `dirty()` to mark the diagram unsaved.

Mirrors the page-level `handleRelationshipSave` flow other notations
use (DRY).

### B. Default edge type for BPMN is sequence_flow (issue #46 item #9)

`UnifiedCanvas`'s `defaultEdgeType` $derived had cases for `uml`,
`archimate`, default `'uses'` — no BPMN case. Handle-drag
connections in BPMN views landed as type `'uses'`, and the
validator's "no outgoing sequence flow" rule (filters by
`e.type === 'sequence_flow'`) kept firing.

The amendment adds a leading `notation === 'bpmn' ? 'sequence_flow'`
arm. Combined with §A above, BPMN edges are now correctly typed both
locally (in canvas state) and remotely (in the relationship record).

### C. Problems panel layout — flex-shrink: 0 (issue #46 items #6 + #7)

`.bpmn-shell__problems` had `max-height: 200px` and `overflow-y: auto`
from v5.4.0, but the flex algorithm in the parent column ignored the
cap and grew the panel to fit content, sending overflow back to the
page. Adding `flex-shrink: 0` makes the cap stick.

### D. Event trigger flyout (issue #46 item #11)

The 60-cell `EventMatrixPicker` dialog was too heavy for the common
flow — the user had already chosen the position by clicking
`Start Event` / `Intermediate Event` / `End Event` in the palette, so
5/6 rows of the matrix were noise.

The new `EventTriggerFlyout.svelte` is a compact ContextPad-style row
of trigger glyph buttons that appears next to the just-placed node.
Renders only the legal triggers for the chosen position (filtered via
the existing `isLegal` logic, now extracted into the shared
`bpmnEventModel.ts` for reuse). On pick: patches
`node.data.data.eventTrigger`. On dismiss (Esc / outside-click /
close): the placed node keeps its default `none` trigger.

`EventMatrixPicker` is retained for the Ctrl-N command-palette
advanced flow but is no longer auto-opened on palette drop / click.

### E. ContextPad action error visibility (issue #46 item #8)

`createBpmnElement`'s catch now also `console.error`s the underlying
exception in addition to setting `toastMessage`, so silent ContextPad
no-ops are diagnosable in production browsers when the toast is
missed (focus loss, repeated set, etc).

### F. Trio gating on BPMN (issue #46 item #12)

The trio's "Add Element" button is hidden when `notation === 'bpmn'`
because the BPMN palette sidebar already covers element creation.
"Link Element" and "Add Diagram" remain — they have distinct semantics
(bind an existing repository element to a node; insert a `call_activity`
sub-process reference).

### G. Trio duplication removed (issue #46 item #5)

The parent canvas toolbar's trio (in the canvas `{:else}` branch)
already covers all non-sequence canvases, including Text and BPMN.
v5.4.0 mistakenly added duplicate trios in the Text and BPMN inner
branches. The duplicates have been removed; the trio now renders
exactly once outside the FocusView (which has its own intentional
toolbar duplicate because the focus overlay hides the parent).

## Amendment 2026-05-08 — v5.6.2 BPMN-03 root cause (issue #69)

### A. Drag-handle connections were silently typeless

User report (#69): "connecting start node to task, the connector does
not register even though edges are connected and the problem bar still
gives a warning."

Root cause — discovered while triaging closed BPMN bugs against current
`main`:

1. xyflow svelte's `Handle.svelte` runs `store.addEdge(connection)`
   immediately after `isValidConnection` returns true (Handle.svelte:108).
2. The `addEdge` util in `@xyflow/system` (index.mjs:1048) does
   `edges.concat({ ...edgeParams, id: getEdgeId(...) })` — it does **not**
   apply `defaultEdgeOptions`. The Connection object only carries
   `{source, target, sourceHandle, targetHandle}`, so the auto-added edge
   has **no `type` field**.
3. `validateBpmn`'s `isSequence(e)` keys on `e.type === 'sequence_flow'`.
   The type-less auto-added edge fails the check; `outDeg` for the source
   stays at 0; "no outgoing sequence flow" warning persists despite the
   user having drawn the edge.
4. `BpmnAuthoringShell.handleBpmnConnect` was wired to `onconnectnodes`,
   which is a **custom prop** on UnifiedCanvas — not a real SvelteFlow
   event. `onconnectnodes` only fires from `handleConnect` in
   UnifiedCanvas, which only gets called from KeyboardHandler (keyboard
   shortcut C) or `handleNodeClick` connect-mode. Drag-handle connections
   never went through `handleConnect` because `<SvelteFlow>` had **no
   `onconnect` prop wired**. So `handleBpmnConnect` never fired on drag,
   `/api/relationships` was never POSTed, and `/elements/<id>`'s
   Relationships panel stayed empty.

This affected **every notation**, not just BPMN — non-BPMN canvases got
type-less edges too, but no validator surfaced the issue, so it went
unnoticed.

### B. Fix

1. **New helper** `frontend/src/lib/canvas/edgeOnConnect.ts` —
   `patchConnectedEdgeType(edges, connection, defaultEdgeType)` is a pure
   function that upgrades the just-added type-less edge to carry
   `type: defaultEdgeType` (and `data.relationshipType` for legacy
   readers). Idempotent — re-running on an already-typed edge is a no-op.
2. **UnifiedCanvas** wires `onconnect={handleSvelteFlowConnect}` on the
   editing `<SvelteFlow>`. The handler calls `patchConnectedEdgeType` then
   notifies the consumer via `onconnectnodes?.(c.source, c.target)` so
   the BPMN shell's relationship POST chain still fires.
3. **BpmnAuthoringShell.handleBpmnConnect** no longer appends a fresh
   edge (UnifiedCanvas now owns edge addition). It POSTs
   `/api/relationships` and patches the existing edge with the resulting
   `relationshipId` so `/elements/<id>` can resolve back.

### C. Why static-parser tests didn't catch this

The v5.4.1 fix (issue #46/9 + #46/10) shipped two tests:
`bpmnDefaultEdgeType.test.ts` and `bpmnConnectRelationship.test.ts`.
Both are static-parser style — they grep the source for code patterns
(`/notation === 'bpmn'.*'sequence_flow'/`,
`/onconnectnodes\s*=\s*\{/`) and pass when the right strings are
present. **They never exercise the runtime wiring** between SvelteFlow's
drag-connect events and the consumer handler chain. The strings were
all present; the chain wasn't connected.

This is the user's frustration in #69 — "barely any of the fixes have
been resolved" — captured precisely. v5.6.2 introduces:
- A pure unit-tested helper (`patchConnectedEdgeType`) — 8 specs
- A static guard (`canvasOnConnectWiring.test.ts`) that fails if the
  `<SvelteFlow>` `onconnect` wiring is dropped — 4 specs
- An updated `bpmnConnectRelationship.test.ts` that asserts the new
  edge-patching contract (no longer appends, maps + sets relationshipId)

The static guards remain a regression net rather than a behavioural
proof — for that, the planned local-backend Playwright harness
(ADR-149, deferred from #69) closes the loop end-to-end.

### D. Bugs transitively closed

The Wave A fix closes four entries in the issue #69 consolidated bug
ledger:
- BPMN-01 (default edge type wasn't applied to drag-handle edges)
- BPMN-02 (POST `/api/relationships` never fired from drag-handle)
- BPMN-03 (the headline reproducer)
- BPMN-09 (`/elements/<id>` Relationships empty, downstream of -02)

Remaining ledger items (BPMN-04/08 — ContextPad append no-op;
entityId-on-Element-POST-failure surfacing) and medium-priority items
(BPMN-05..17) are tracked for follow-up waves; v5.6.2 ships only the
critical-path fix.
