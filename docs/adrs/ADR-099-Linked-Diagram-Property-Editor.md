# ADR-099: Linked Diagram Property Editor

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-099 |
| **Initiative** | Linked Diagram Property Editor |
| **Proposed By** | Engineering |
| **Date** | 2026-03-22 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the diagram canvas edit mode, where nodes can link to other diagrams via `linkedModelId` for browse-mode navigation,

**facing** the inability to set, change, or clear a node's linked diagram through the UI — requiring SQL or API workarounds to fix broken or missing navigation links,

**we decided for** adding a `LinkedDiagramPanel` component to the existing edit sidebar, reusing the `nodedatachange` CustomEvent pattern and the existing `DiagramPicker` component,

**and neglected** embedding the diagram picker inside `ElementEditPanel` (which would bloat an already complex component with linked/unlinked modes), and creating a new event type (unnecessary since `nodedatachange` already handles arbitrary field updates),

**to achieve** direct UI-based control over node diagram links, with undo support and automatic persistence via the existing canvas save flow,

**accepting that** resolving the linked diagram name requires a lightweight API call per node selection (acceptable for UX responsiveness).

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| Linked Diagram Editor | Set/change/clear linkedModelId from edit sidebar | [SPEC-099-A](./specs/SPEC-099-A-Linked-Diagram-Editor.md) |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Relates To | ADR-091 | Icon Library & Node Resize | Node edit sidebar pattern |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Approved | Engineering | 2026-03-22 |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
