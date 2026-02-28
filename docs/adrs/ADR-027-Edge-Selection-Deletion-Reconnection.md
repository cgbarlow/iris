# ADR-027: Edge Selection, Deletion, and Reconnection

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-027 |
| **Initiative** | Edge Selection, Deletion, and Reconnection |
| **Proposed By** | Architecture Team |
| **Date** | 2026-02-28 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris canvas system where edges (relationships between entities) cannot be independently selected, deleted, or reconnected — users must delete a connected node to remove an edge, and have no way to redirect an edge endpoint to a different node,

**facing** the need for granular edge manipulation so users can correct modelling mistakes, reorganise relationships without destroying entities, and efficiently restructure diagrams by dragging edge endpoints to new targets,

**we decided for** extending the canvas components (ModelCanvas, FullViewCanvas, KeyboardHandler) with edge selection state, edge click handling, edge deletion (both via toolbar button and keyboard Delete/Backspace), and edge reconnection via the @xyflow/svelte `edgesReconnectable` prop and `onreconnect` event,

**and neglected** implementing a custom drag-based reconnection system (unnecessary given @xyflow/svelte's built-in support), adding edge editing dialogs for changing relationship type on reconnect (can be added later as a separate feature), and multi-edge selection (out of scope for initial implementation),

**to achieve** full edge lifecycle management — select, delete, and reconnect — giving users the same level of control over edges as they already have over nodes, with keyboard accessibility and screen reader announcements for all operations,

**accepting that** reconnection does not trigger the RelationshipDialog (relationship type is preserved from the original edge), and multi-edge selection is deferred to a future iteration.

---

## Options Considered

### Edge Deletion

#### Option 1: Toolbar Button + Keyboard Delete (Selected)

**Pros:**
- Consistent with existing node deletion pattern (keyboard + UI)
- Accessible via both mouse and keyboard
- Toolbar button provides clear visual affordance

**Cons:**
- Requires tracking selectedEdgeId state alongside selectedNodeId

**Why selected:** Matches the established interaction patterns for node operations and maintains full keyboard accessibility.

#### Option 2: Context Menu on Edge (Rejected)

**Pros:**
- Familiar right-click pattern

**Cons:**
- Poor keyboard accessibility
- Requires implementing a context menu system
- Inconsistent with existing node deletion pattern

**Why rejected:** Does not meet WCAG keyboard accessibility requirements and adds unnecessary complexity.

### Edge Reconnection

#### Option 1: @xyflow/svelte Built-in Reconnection (Selected)

**Pros:**
- Native support via `edgesReconnectable` prop
- Handles all drag interaction details
- Well-tested library feature

**Cons:**
- Limited customisation of reconnection UI

**Why selected:** The library provides exactly this feature out of the box with minimal integration effort.

#### Option 2: Custom Drag Implementation (Rejected)

**Pros:**
- Full control over interaction and visuals

**Cons:**
- Significant implementation effort
- Must handle all pointer events, hit testing, snapping
- Likely to have edge cases and bugs

**Why rejected:** Reimplementing existing library functionality adds unnecessary risk and effort.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-28 | Accepted | Implement edge operations | 6 months | 2026-08-28 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Architecture Team | 2026-02-28 |
| Accepted | Project Lead | 2026-02-28 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Depends On | ADR-002 | Frontend Tech Stack | Uses Svelte 5 runes and @xyflow/svelte |
| Depends On | ADR-011 | Canvas Integration and Testing Strategy | Extends canvas interaction patterns |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-027-A | Edge Operations | Technical Specification | [specs/SPEC-027-A-Edge-Operations.md](specs/SPEC-027-A-Edge-Operations.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
