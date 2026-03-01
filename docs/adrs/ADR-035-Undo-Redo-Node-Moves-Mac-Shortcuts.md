# ADR-035: Undo/Redo Node Moves + Mac Shortcut Labels

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-035 |
| **Initiative** | Complete Undo/Redo Coverage and Cross-Platform Shortcut Labels |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris canvas editor where ADR-028 introduced undo/redo for add, delete, and link operations but omitted node drag moves, meaning users who reposition nodes via mouse drag have no way to undo accidental moves without discarding all unsaved changes,

**facing** two gaps: (a) node drags are the most frequent canvas operation yet produce no undo history entry, making the undo feature feel incomplete, and (b) Undo/Redo button tooltips display "Ctrl+Z" / "Ctrl+Y" which is incorrect for macOS users who expect Cmd+Z / Cmd+Y,

**we decided for** capturing the pre-drag canvas snapshot via the `onnodedragstart` SvelteFlow event (propagated from `<SvelteFlow>` through ModelCanvas/FullViewCanvas to the model detail page where `history.pushState()` and `canvasDirty = true` are called), and updating all Undo/Redo button `title` attributes from "Ctrl+Z" / "Ctrl+Y" to "Ctrl/Cmd+Z" / "Ctrl/Cmd+Y",

**and neglected** (1) capturing state on every drag tick (`onnodedrag`) which would flood the undo stack with intermediate positions, (2) capturing on drag end (`onnodedragstop`) which would record the post-move state rather than the pre-move state needed for undo, and (3) runtime platform detection (`navigator.platform`) to show only "Cmd" on Mac vs "Ctrl" on others, due to added complexity for marginal UX benefit,

**to achieve** complete undo/redo coverage for all canvas mutations including the most common operation (node repositioning), with correct cross-platform shortcut labelling that is accurate on both Windows/Linux and macOS,

**accepting that** the static "Ctrl/Cmd" label is slightly verbose compared to platform-specific labels, and that multi-node drags will capture a single snapshot (the entire node/edge state before the drag began), which is the correct granularity for undo.

---

## Options Considered

### Option 1: `onnodedragstart` Snapshot (Selected)

**Pros:**
- Captures state before the drag begins, which is exactly what undo needs to restore
- Fires once per drag operation, not per pixel of movement
- Uses the existing `history.pushState()` infrastructure from ADR-028
- Minimal code change: add one prop and one event handler

**Cons:**
- Pushes a snapshot even for trivial/accidental drags (mitigated by MAX_HISTORY cap)

**Why selected:** Correct semantic timing (pre-mutation snapshot), minimal complexity, reuses existing infrastructure.

### Option 2: `onnodedragstop` Snapshot (Rejected)

**Pros:**
- Could filter out no-op drags by comparing start and end positions

**Cons:**
- Fires after the move completes, so the snapshot would contain the new positions, not the old ones
- Would require a separate mechanism to capture the pre-drag state

**Why rejected:** Wrong timing for snapshot-based undo. The pre-drag state must be captured before the mutation occurs.

### Option 3: `onnodedrag` Continuous Tracking (Rejected)

**Pros:**
- Could provide per-pixel undo granularity

**Cons:**
- Fires on every mouse move during drag, flooding the undo stack
- Would require debouncing/coalescing logic
- Excessive memory usage and poor undo UX (user would have to undo hundreds of micro-moves)

**Why rejected:** Completely wrong granularity for undo operations.

### Option 4: Runtime Platform Detection for Shortcut Labels (Rejected)

**Pros:**
- Shows exactly "Cmd+Z" on Mac, "Ctrl+Z" on Windows/Linux

**Cons:**
- `navigator.platform` is deprecated; `navigator.userAgentData.platform` is not universally supported
- Requires SSR-safe guards (window/navigator unavailable during server-side rendering)
- Additional complexity for a cosmetic improvement

**Why rejected:** The static "Ctrl/Cmd" label is universally correct and avoids platform detection complexity.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-03-01 | Accepted | Implement node drag undo + shortcut labels | 6 months | 2026-09-01 |

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
| Extends | ADR-028 | Canvas Undo/Redo | Adds node drag to existing undo/redo infrastructure |
| Depends On | ADR-002 | Frontend Tech Stack | Uses Svelte 5 runes and @xyflow/svelte |
| Depends On | ADR-011 | Canvas Integration and Testing Strategy | Extends canvas interaction patterns |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-035-A | Undo/Redo Node Moves + Mac Shortcuts | Technical Specification | [specs/SPEC-035-A-Undo-Node-Moves-Mac-Shortcuts.md](specs/SPEC-035-A-Undo-Node-Moves-Mac-Shortcuts.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
