# ADR-101: Visual Toggles — Description Display & Element Count Badge

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-101 |
| **Initiative** | Visual Toggles |
| **Proposed By** | Engineering |
| **Date** | 2026-03-23 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris canvas rendering system, where nodes display labels, descriptions, and visual metadata,

**facing** the need for DoView nodes to hide descriptions by default (since DoView outcome labels are self-descriptive), and the desire to show element reuse counts on nodes to help users understand cross-diagram relationships,

**we decided for** extending the theme rendering config with a `hideDescription` toggle (defaulting to true for DoView), adding a per-node override toggle in the edit sidebar, and adding a user-level "Display element count" setting that shows a diagram usage count badge on each node,

**and neglected** making description visibility a global-only setting (too coarse — different notations need different defaults), and computing element count client-side by scanning all diagrams (expensive and inaccurate),

**to achieve** notation-appropriate default description display, per-node override control in edit mode, and at-a-glance element reuse visibility controlled by user preference,

**accepting that** the element count badge requires an additional data field populated during diagram load, and the user setting is stored in localStorage (client-side only, no cross-device sync).

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| Hide Description Toggle | Theme-level default + per-node override in edit sidebar | [SPEC-101-A](./specs/SPEC-101-A-Visual-Toggles.md) |
| Element Count Badge | Diagram usage count in node top-right, controlled by user setting | [SPEC-101-A](./specs/SPEC-101-A-Visual-Toggles.md) |
| Visual Toggles Settings | New settings section between Default Notation and Change Password | [SPEC-101-A](./specs/SPEC-101-A-Visual-Toggles.md) |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-094 | DoView Notation & AI Creation | DoView theme config |
| Depends On | ADR-100 | DoView Element-Backed Nodes | entityId + diagram_usage_count |
| Relates To | ADR-085 | Theme System | ThemeRenderingConfig extension |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Approved | Engineering | 2026-03-23 |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
