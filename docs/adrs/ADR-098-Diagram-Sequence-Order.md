# ADR-098: Diagram Sequence Order

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-098 |
| **Initiative** | Diagram Sequence Order |
| **Proposed By** | Engineering |
| **Date** | 2026-03-22 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the navigation hierarchy tree on the dashboard, which displays diagrams and packages in a nested tree structure,

**facing** the limitation that diagrams and packages are sorted alphabetically by name with no user control over ordering, making it impossible to arrange items in a logical sequence within a package,

**we decided for** adding a `sequence_order` integer column to both `diagrams` and `packages` tables, with a `PUT /api/diagrams/reorder` endpoint and HTML5 drag-and-drop in the TreeNode component,

**and neglected** adding a third-party sortable library (unnecessary weight for a simple tree reorder) and server-side drag-drop via WebSocket (over-engineered for infrequent reordering),

**to achieve** user-controllable ordering of diagrams and packages within the navigation tree, defaulting to creation order,

**accepting that** HTML5 drag-and-drop has limited mobile support (acceptable for a desktop-first tool) and that reordering sends the full sibling list per parent (acceptable for typical package sizes).

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| Sequence order | User-controllable ordering of diagrams/packages in navigation tree | [SPEC-098-A](./specs/SPEC-098-A-Sequence-Order.md) |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Relates To | ADR-076 | Dashboard Hierarchy Tree | Hierarchy tree display |
| Relates To | ADR-055 | Model Hierarchy | Hierarchy data model |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-098-A | Sequence Order | Technical Specification | [specs/SPEC-098-A-Sequence-Order.md](./specs/SPEC-098-A-Sequence-Order.md) |
| GitHub | Issue #7 | Feature Request | Sequence order for diagrams in navigation view |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Approved | Engineering | 2026-03-22 |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
