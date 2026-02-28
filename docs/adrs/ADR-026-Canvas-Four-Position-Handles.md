# ADR-026: Canvas Four-Position Connection Handles

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-026 |
| **Initiative** | Canvas Four-Position Connection Handles |
| **Proposed By** | Architecture Team |
| **Date** | 2026-02-28 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris canvas where all node components only expose connection handles at Position.Top (target) and Position.Bottom (source), limiting edge connections to vertical top-down flows,

**facing** the need for users to create horizontal and diagonal connections between nodes to accurately represent architecture relationships that do not follow a strict top-to-bottom layout, such as peer-to-peer service communication, lateral dependencies, and bidirectional data flows,

**we decided for** adding four connection handles to every canvas node — top (target), bottom (source), left (target), and right (source) — with unique `id` attributes and `connectionMode="loose"` on SvelteFlow to allow edges to attach to any handle,

**and neglected** keeping only two handles and relying on edge routing to visually approximate horizontal connections (which produces awkward curved paths), and adding handles dynamically based on existing connections (which adds state management complexity without clear UX benefit),

**to achieve** flexible multi-directional edge connections that let users model architecture relationships from any side of a node, improving diagram clarity and layout freedom,

**accepting that** nodes will display four visible handle dots instead of two, which slightly increases visual density, and that existing edges connected without explicit handle IDs will fall back to default handle selection by the xyflow library.

---

## Options Considered

### Option 1: Four Static Handles on All Nodes (Selected)

**Pros:**
- Simple, consistent implementation across all 14 node types
- Users can connect from any direction immediately
- `connectionMode="loose"` allows source-to-source and target-to-target connections for maximum flexibility
- Unique `id` attributes enable explicit handle targeting in edge data

**Cons:**
- Four handle dots visible on every node (minor visual density increase)
- No per-node customisation of which sides allow connections

### Option 2: Keep Two Handles, Improve Edge Routing (Rejected)

**Pros:**
- No visual change to nodes
- Fewer DOM elements per node

**Cons:**
- Horizontal connections still produce awkward curved paths routed through top/bottom
- Does not solve the fundamental layout limitation
- Users cannot express connection intent (which side the edge should attach to)

**Why rejected:** Does not address the core problem — users need to connect nodes from any side.

### Option 3: Dynamic Handles Based on Connected Edges (Rejected)

**Pros:**
- Only shows handles where connections exist, reducing visual clutter
- Theoretically cleaner appearance

**Cons:**
- Requires tracking edge-to-handle mappings in state
- Chicken-and-egg problem: handle must exist before user can drag to create an edge
- Significantly more complex implementation for marginal visual benefit

**Why rejected:** Handles must exist before connections can be made, making the dynamic approach impractical for edge creation workflows.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-28 | Accepted | Add four-position handles to all canvas nodes | 6 months | 2026-08-28 |

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
| Depends On | ADR-011 | Canvas Integration and Testing Strategy | Canvas node architecture established here |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-026-A | Four-Position Handles Implementation | Technical Specification | [specs/SPEC-026-A-Four-Position-Handles.md](specs/SPEC-026-A-Four-Position-Handles.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
