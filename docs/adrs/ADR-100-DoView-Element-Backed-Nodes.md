# ADR-100: DoView Element-Backed Nodes

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-100 |
| **Initiative** | DoView Element-Backed Nodes |
| **Proposed By** | Engineering |
| **Date** | 2026-03-23 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** DoView notation diagrams, where diagram nodes represent outcomes, final outcomes, overview tiles, and source references,

**facing** the problem that DoView diagram nodes lack `entityId` linkage to element records — preventing cross-diagram element reuse, breaking diagram-entity relationship tracking, and leaving EntityDetailPanel unable to display element details or "Used in Diagrams" for DoView nodes,

**we decided for** creating backing element and relationship records for every DoView diagram node in both seed data and AI diagram creation, using the same `_e(eids, nid)` pattern established by Simple, UML, ArchiMate, and C4 notations,

**and neglected** leaving nodes as standalone canvas annotations (status quo — perpetuates the broken integration), and lazy-materialising elements on first user click (adds UI complexity and deferred state management),

**to achieve** full diagram-entity integration for DoView, cross-diagram element reuse (same outcome appearing on multiple diagrams), accurate `diagram_usage_count`, working EntityDetailPanel for DoView nodes, and relationship tracking for causal links,

**accepting that** the element count in seed data increases from 66 to 87, and AI diagram creation becomes slightly more complex with an additional materialisation phase.

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| Seed Element Linkage | All DoView seed nodes backed by elements with entityId | [SPEC-100-A](./specs/SPEC-100-A-DoView-Element-Backed-Nodes.md) |
| AI Creation Materialisation | AI-created DoView diagrams auto-create elements and relationships | [SPEC-100-A](./specs/SPEC-100-A-DoView-Element-Backed-Nodes.md) |
| Cross-Diagram Reuse | Same element referenced by multiple diagrams via shared entityId | [SPEC-100-A](./specs/SPEC-100-A-DoView-Element-Backed-Nodes.md) |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-094 | DoView Notation & AI Creation | DoView notation foundation |
| Relates To | ADR-079 | Notation Registry | Element-notation linkage |
| Relates To | ADR-081 | Notation-First UX | EntityDetailPanel integration |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Approved | Engineering | 2026-03-23 |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
