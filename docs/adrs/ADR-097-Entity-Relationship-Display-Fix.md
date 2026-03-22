# ADR-097: Entity Relationship Display Fix

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-097 |
| **Initiative** | Entity Relationship Display Fix |
| **Proposed By** | Engineering |
| **Date** | 2026-03-22 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the Relationships tab on the diagram detail page, which should display entity-to-entity relationships for elements present on the diagram's canvas,

**facing** a bug where the backend function `list_element_relationships_for_diagram` extracts element IDs from canvas nodes using the field name `elementId`, while the frontend and all other backend code stores the entity reference as `entityId` in `CanvasNodeData`, resulting in zero element IDs being found and no relationships ever being returned,

**we decided for** correcting the field name from `elementId` to `entityId` in `backend/app/package_relationships/service.py:113` to match the canonical field name used throughout the codebase,

**and neglected** renaming the frontend field to `elementId` (which would require changes across 20+ files in the frontend and backend, versus a single-line fix),

**to achieve** correct display of entity-to-entity relationships in the Relationships tab when viewing any diagram that contains entity nodes with existing relationships,

**accepting that** this is a straightforward field name correction with no architectural trade-offs.

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| Field name fix | Correct `elementId` → `entityId` in relationship query | [SPEC-097-A](./specs/SPEC-097-A-Relationship-Field-Fix.md) |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Relates To | ADR-067 | Unified Relationship Management | Relationship display is part of unified management |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-097-A | Relationship Field Fix | Technical Specification | [specs/SPEC-097-A-Relationship-Field-Fix.md](./specs/SPEC-097-A-Relationship-Field-Fix.md) |
| GitHub | Issue #4 | Bug Report | Entity relationships not displayed in diagram view |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Approved | Engineering | 2026-03-22 |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
