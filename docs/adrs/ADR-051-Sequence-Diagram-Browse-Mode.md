# ADR-051: Sequence Diagram Browse Mode

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-051 |
| **Initiative** | Sequence Diagram Browse Mode (WP-7) |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris browse mode where clicking a canvas node opens the `EntityDetailPanel` to display the backing entity's metadata, but sequence diagram participants rendered as SVG `<g>` elements inside the `SequenceDiagram` component are not interactive and do not integrate with the entity detail panel,

**facing** the need for sequence diagram participants to be clickable in browse mode so users can inspect the entity behind each participant without switching to the entity list,

**we decided for** an `onparticipantselect` callback prop on the `SequenceDiagram` component that is invoked when a user clicks a participant's `<g>` element, with a click handler attached to each participant group during rendering that maps the clicked participant to a synthetic `CanvasNode` object (containing the entity ID, name, and type), which is then passed to the existing `EntityDetailPanel` for display,

**and neglected** converting sequence diagram participants to @xyflow/svelte nodes (sequence diagrams use a custom SVG renderer, not @xyflow/svelte, making this architecturally incompatible), opening a separate modal for participant details (inconsistent with the sidebar panel pattern used in canvas browse mode), and deep-linking to the entity detail page on click (breaks the browse context and navigates away from the model),

**to achieve** a consistent browse-mode interaction pattern where clicking any visual element representing an entity -- whether a canvas node or a sequence diagram participant -- opens the same `EntityDetailPanel` sidebar with entity metadata,

**accepting that** the synthetic `CanvasNode` is a lightweight adapter object (not a real canvas node) created solely to satisfy `EntityDetailPanel`'s input contract, that only participant headers are clickable (not message arrows or activation bars), and that the click handler relies on participants having a resolvable entity ID stored in the sequence diagram data.

---

## Options Considered

### Option 1: Callback Prop with Synthetic CanvasNode Mapping (Selected)

**Pros:**
- Reuses the existing `EntityDetailPanel` without modification
- Clean separation via callback prop; `SequenceDiagram` remains presentation-only
- Consistent browse-mode UX across canvas and sequence diagrams
- Minimal coupling between diagram types

**Cons:**
- Synthetic `CanvasNode` is an adapter/shim, not a real canvas node
- Only participant headers are clickable

**Why selected:** Achieves UX consistency with minimal code and no changes to either `EntityDetailPanel` or the core `SequenceDiagram` renderer.

### Option 2: Convert Participants to @xyflow/svelte Nodes (Rejected)

**Pros:**
- Full native node interactivity (selection, drag, etc.)

**Cons:**
- Sequence diagrams use a custom SVG renderer, not @xyflow/svelte
- Would require rewriting the sequence diagram renderer entirely
- Breaks the sequential layout semantics of sequence diagrams

**Why rejected:** Architecturally incompatible; sequence diagrams are not flow graphs.

### Option 3: Navigate to Entity Detail Page on Click (Rejected)

**Pros:**
- Full entity detail view with all tabs and actions

**Cons:**
- Navigates away from the model view
- Inconsistent with canvas browse mode (which uses a sidebar panel)
- User loses diagram context

**Why rejected:** Breaks the in-context browsing pattern established by the canvas.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-03-01 | Accepted | Add participant click handling in sequence diagram browse mode | 6 months | 2026-09-01 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Architecture Team | 2026-03-01 |
| Accepted | Project Lead | 2026-03-01 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Depends On | ADR-023 | Browse-Mode Entity Navigation | EntityDetailPanel reused for participant details |
| Depends On | ADR-014 | Canvas UX Parity | Browse mode interaction patterns extended to sequence diagrams |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
