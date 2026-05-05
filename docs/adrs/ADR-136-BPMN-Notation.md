# ADR-136: BPMN 2.0 notation

Status: Accepted (2026-05-04) — amended 2026-05-05 (issues #27, #33, #37)

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
