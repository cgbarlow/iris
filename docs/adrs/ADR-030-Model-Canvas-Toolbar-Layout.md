# ADR-030: Model Canvas Toolbar Layout

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-030 |
| **Initiative** | Model Edit Toolbar Resequencing |
| **Proposed By** | Architecture Team |
| **Date** | 2026-02-28 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris model canvas toolbar where buttons have been added incrementally by separate work packages (Add Entity, Link Entity, Save, Discard, Focus, and planned Undo/Redo and Delete Edge), resulting in a flat, ungrouped button row that mixes creation actions with persistence controls and view commands,

**facing** the need for a predictable, scannable toolbar layout that groups related actions together so users can quickly locate the action they need — especially as the button count grows with undo/redo and edge deletion features,

**we decided for** organising toolbar buttons into four semantic groups separated by visual gaps:

1. **Create** — content creation actions (Add Entity, Link Entity / Add Participant, Add Message)
2. **Edit** — modification actions (Delete Edge / Delete Selected, Undo, Redo)
3. **Persist** — commit/revert actions (Save, Discard) plus the Unsaved indicator
4. **View** — view controls (Focus), pushed to the rightmost position with `ml-auto`

Groups are wrapped in `<div class="flex items-center gap-2">` containers, and the parent toolbar uses `gap-4` to create visual separation between groups.

**and neglected** keeping buttons in a flat ungrouped row (increasingly hard to scan as count grows), using dropdown menus or collapsible sections (adds interaction cost for frequently-used actions), and using icon-only toolbar buttons (reduces discoverability for new users),

**to achieve** a logically ordered toolbar that follows the natural left-to-right workflow (create content, then modify it, then persist changes, then adjust the view), making all actions predictable and quickly locatable regardless of how many buttons are present,

**accepting that** the visual gap-based grouping is subtle and may not be immediately obvious to all users, and that the Focus button being separated to the far right creates distance from other controls.

---

## Options Considered

### Option 1: Semantic Group Layout with Visual Gaps (Selected)

**Pros:**
- Groups follow natural workflow order (create, edit, persist, view)
- Minimal visual overhead — gap spacing provides separation without heavy dividers
- Consistent pattern across both canvas and sequence toolbars
- Scales well as new buttons are added to existing groups

**Cons:**
- Gap-based separation is subtle compared to explicit dividers
- Requires wrapping divs for each group

**Why selected:** Provides clear logical grouping with minimal visual noise, and the pattern is consistent across all canvas types.

### Option 2: Flat Button Row (Rejected)

**Pros:**
- Simpler markup, no wrapper divs needed
- All buttons equidistant

**Cons:**
- No visual indication of which buttons are related
- Increasingly hard to scan as button count grows
- Mixes unrelated actions (e.g., "Add Entity" next to "Save")

**Why rejected:** Does not scale — the toolbar already has 5+ buttons and will grow further.

### Option 3: Dropdown Menus (Rejected)

**Pros:**
- Compact toolbar footprint
- Clear grouping via menu labels

**Cons:**
- Adds click cost to reach frequently-used actions
- Hides available actions behind menus

**Why rejected:** Toolbar actions are used frequently during editing; hiding them behind menus adds unnecessary friction.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-28 | Accepted | Implement toolbar resequencing | 6 months | 2026-08-28 |

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
| Depends On | ADR-014 | Canvas UX Parity | Focus button and sequence edit toolbar originate here |
| Depends On | ADR-011 | Canvas Integration and Testing Strategy | Canvas toolbar patterns |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-030-A | Toolbar Layout Implementation | Technical Specification | [specs/SPEC-030-A-Toolbar-Layout.md](specs/SPEC-030-A-Toolbar-Layout.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
