# ADR-028: Canvas Undo/Redo

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-028 |
| **Initiative** | Canvas Undo/Redo for Node and Edge Operations |
| **Proposed By** | Architecture Team |
| **Date** | 2026-02-28 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris canvas editor where users add entities, delete nodes, create relationships, and link existing entities — all mutations that directly overwrite canvas state with no ability to reverse accidental changes,

**facing** the need for a standard editing safety net that users expect in any graphical editor, where a misplaced delete or unintended connection cannot be recovered without discarding all unsaved work or manually recreating lost elements,

**we decided for** a client-side undo/redo history manager implemented as a Svelte 5 runes module (`createCanvasHistory`), storing deep-cloned snapshots of `canvasNodes` and `canvasEdges` in bounded undo/redo stacks (max 50 entries), with toolbar buttons and Ctrl+Z / Ctrl+Y keyboard shortcuts integrated into the existing canvas editing flow,

**and neglected** command-pattern undo (individual reversible operation objects), server-side undo via version rollback, and diff-based state compression,

**to achieve** immediate, intuitive undo/redo for all canvas mutations without architectural complexity, preserving the existing direct-state-mutation pattern used throughout the canvas editing code,

**accepting that** snapshot-based history uses more memory than diff-based approaches (mitigated by the 50-entry cap and `structuredClone` for isolation), and that history is cleared on save/discard since the server is the source of truth for persisted state.

---

## Options Considered

### Option 1: Snapshot-Based History (Selected)

**Pros:**
- Simple implementation — push full state before each mutation
- Works with any mutation pattern (no need to define inverse operations)
- Deep clone via `structuredClone` ensures complete isolation
- Bounded stack prevents unbounded memory growth

**Cons:**
- Higher memory usage than diff-based approaches
- Cannot selectively undo individual operations within a batch

**Why selected:** Matches the existing direct-state-mutation pattern. All canvas mutations (`canvasNodes = [...]`) are simple reassignments, making pre-mutation snapshots the natural undo unit.

### Option 2: Command Pattern (Rejected)

**Pros:**
- Lower memory usage (stores operations, not full state)
- Can provide richer undo descriptions

**Cons:**
- Requires defining inverse operations for every mutation type
- Complex to maintain as new mutation types are added
- Edge cases with dependent operations (e.g., deleting a node must also undo edge removal)

**Why rejected:** Disproportionate complexity for the current set of canvas operations.

### Option 3: Server-Side Version Rollback (Rejected)

**Pros:**
- Leverages existing versioning infrastructure

**Cons:**
- Requires a save for every operation (poor UX, excessive API calls)
- Cannot undo unsaved work
- Network latency makes undo feel sluggish

**Why rejected:** Undo must be instantaneous and work on unsaved local state.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-28 | Accepted | Implement snapshot-based undo/redo | 6 months | 2026-08-28 |

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
| Depends On | ADR-002 | Frontend Tech Stack | Uses Svelte 5 runes for reactive state |
| Depends On | ADR-011 | Canvas Integration and Testing Strategy | Extends canvas interaction patterns |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-028-A | Canvas Undo/Redo Implementation | Technical Specification | [specs/SPEC-028-A-Canvas-Undo-Redo.md](specs/SPEC-028-A-Canvas-Undo-Redo.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
