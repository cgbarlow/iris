# ADR-038: Edge Reconnection Fix

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-038 |
| **Initiative** | Edge Reconnection Fix (WP-4) |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris canvas editor where edge reconnection (dragging an edge endpoint to a new node) was implemented in ADR-027 with an `onreconnect` handler in ModelCanvas and FullViewCanvas, but the feature does not work because users cannot grab edge endpoints to initiate a reconnection drag,

**facing** the root cause that @xyflow/svelte v1.5.x does not provide an `edgesReconnectable` prop on `<SvelteFlow>` — instead, edge endpoints become draggable only when custom edge components render `EdgeReconnectAnchor` components (exported from `@xyflow/svelte`) at their source and target positions, and none of the project's custom edge components currently include these anchors,

**we decided for** adding `EdgeReconnectAnchor` components (with `type="source"` and `type="target"`) to all custom edge components across Simple View (5 edges), UML (6 edges), and ArchiMate (1 shared edge), and ensuring the `handleReconnect` function in both canvas components pushes state to the undo history before modifying edges,

**and neglected** reverting to @xyflow/svelte's built-in default edges which include reconnect anchors by default (would lose all custom styling — dash patterns, labels, markers), and adding a global `edgesReconnectable` prop (does not exist in the v1.5.x API despite being referenced in ADR-027's specification),

**to achieve** working edge reconnection where users can hover over edge endpoints to reveal grab handles, drag them to a different node, and have the operation recorded in undo history for safe reversal,

**accepting that** each custom edge component gains a small amount of additional markup (two `EdgeReconnectAnchor` elements), and that the reconnection anchors use the library's default styling and sizing.

---

## Options Considered

### Option 1: Add EdgeReconnectAnchor to Custom Edge Components (Selected)

**Pros:**
- Uses the library's official API for enabling edge reconnection
- Preserves all custom edge styling (dash patterns, labels, aria attributes)
- Works with the existing `onreconnect` handler already in place
- Minimal code change per edge component (add import + two elements)

**Cons:**
- Must update every custom edge component (12 files total)
- EdgeReconnectAnchor positioning requires source/target coordinates from EdgeProps

**Why selected:** This is the correct approach per @xyflow/svelte v1.5.x architecture. The library requires explicit opt-in at the edge component level.

### Option 2: Replace Custom Edges with Built-in Edges (Rejected)

**Pros:**
- Built-in edges include reconnect anchors by default
- Fewer components to maintain

**Cons:**
- Loses all custom styling (dash patterns differ per relationship type)
- Loses custom ARIA labels per edge type
- Loses edge label rendering via textPath
- Would require re-implementing all visual differentiation via CSS

**Why rejected:** Custom edge styling is a core feature of the canvas — each relationship type has distinct visual treatment.

### Option 3: Monkey-patch edgesReconnectable Prop (Rejected)

**Pros:**
- Single-line change if the prop existed

**Cons:**
- The prop does not exist in @xyflow/svelte v1.5.x
- Would not work and would produce a TypeScript error
- Based on incorrect API assumption from ADR-027

**Why rejected:** The prop simply does not exist in the installed version of the library.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-03-01 | Accepted | Add EdgeReconnectAnchor to all edge components | 6 months | 2026-09-01 |

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
| Depends On | ADR-027 | Edge Selection, Deletion, and Reconnection | Original edge operations ADR; this fixes the reconnection portion |
| Depends On | ADR-028 | Canvas Undo/Redo | Reconnection must push to undo history |
| Supersedes (partial) | ADR-027 | Edge Selection, Deletion, and Reconnection | Corrects the implementation approach for reconnection (EdgeReconnectAnchor instead of edgesReconnectable prop) |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-038-A | Edge Reconnection Fix | Technical Specification | [specs/SPEC-038-A-Edge-Reconnection-Fix.md](specs/SPEC-038-A-Edge-Reconnection-Fix.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
