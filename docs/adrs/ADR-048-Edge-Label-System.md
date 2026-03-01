# ADR-048: Edge Label System

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-048 |
| **Initiative** | Edge Label System (WP-3, WP-4) |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris model canvas where edges (connectors) between nodes currently have no user-visible labels, making it impossible to annotate the nature of relationships (e.g., "depends on", "calls", "extends") directly on the diagram,

**facing** the need for users to add, edit, and freely position text labels on edges so that relationship semantics are visible without opening a detail panel,

**we decided for** (WP-3) an `EdgeLabel.svelte` shared component rendered via @xyflow/svelte's `EdgeLabelRenderer`, supporting double-click to enter inline edit mode, dispatching a `CustomEvent` with the updated label text on blur or Enter key, integrated into all custom edge types; (WP-4) `labelOffsetX`, `labelOffsetY`, and `labelRotation` fields added to `CanvasEdgeData`, with drag-to-reposition via pointer events (`pointerdown`/`pointermove`/`pointerup`) on the label element that update the offset values and persist them with the canvas layout,

**and neglected** using native SVG `<text>` elements directly on the edge path (limited styling, no HTML input for editing, poor accessibility), a separate label dialog/modal (breaks the direct manipulation mental model), and fixed label positions at the edge midpoint only (insufficient for complex diagrams where labels overlap nodes or other edges),

**to achieve** inline edge labelling with direct manipulation for both text content and spatial positioning, persisted as part of the canvas data model and rendered consistently in both edit and browse modes,

**accepting that** the `EdgeLabelRenderer` creates a DOM overlay outside the SVG layer (which means labels do not scale with SVG zoom but remain readable at all zoom levels), drag repositioning uses pixel offsets relative to the edge midpoint (not percentage-based), and label rotation is a numeric degree value that users set via drag gesture rather than a precise input.

---

## Options Considered

### Option 1: EdgeLabelRenderer with Drag Repositioning (Selected)

**Pros:**
- Uses @xyflow/svelte's built-in `EdgeLabelRenderer` for correct positioning
- HTML-based labels support rich text input and accessibility
- Double-click to edit is a familiar interaction pattern
- Drag offsets provide free-form positioning
- Labels remain readable at any zoom level

**Cons:**
- Labels are in a DOM overlay, not inline SVG
- Offset persistence adds fields to `CanvasEdgeData`

**Why selected:** Best balance of usability, accessibility, and integration with the existing @xyflow/svelte architecture.

### Option 2: SVG `<text>` on Edge Path (Rejected)

**Pros:**
- Labels render inline with the SVG canvas
- Scale with zoom naturally

**Cons:**
- No native HTML input for editing; would require custom SVG text editing
- Limited styling options (no word wrap, no rich formatting)
- Poor accessibility (screen readers handle SVG text inconsistently)

**Why rejected:** Editing SVG text inline is complex and produces a worse user experience than HTML overlays.

### Option 3: Label Dialog/Modal (Rejected)

**Pros:**
- Full-featured text input with validation
- Familiar modal pattern

**Cons:**
- Breaks direct manipulation; user loses context of which edge they are labelling
- Extra click to open and close dialog
- Cannot see label position relative to the diagram while editing

**Why rejected:** Indirect editing flow is inferior for a spatial tool where context matters.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-03-01 | Accepted | Add edge label editing and repositioning | 6 months | 2026-09-01 |

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
| Depends On | ADR-027 | Edge Selection Deletion Reconnection | Edge label system extends edge interaction capabilities |
| Depends On | ADR-042 | Connector Manipulation | Edge data model extended with label fields |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
