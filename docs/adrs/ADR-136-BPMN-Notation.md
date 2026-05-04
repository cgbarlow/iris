# ADR-136: BPMN 2.0 notation

Status: Accepted (2026-05-04)

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
