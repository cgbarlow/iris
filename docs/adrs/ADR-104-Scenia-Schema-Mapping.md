# ADR-104: Scenia Schema Mapping

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-104 |
| **Initiative** | Scenia Schema Mapping |
| **Proposed By** | Engineering |
| **Date** | 2026-03-25 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** integrating the Scenia roadmapping tool with Iris,

**facing** the need to store Scenia data persistently in the Iris database rather than IndexedDB,

**we decided for** storing Scenia entities as Iris elements (using element_type prefix "scenia_") with JSON data columns, plus dedicated tables for timeline settings, versions, asset categories, and application statuses,

**and neglected** a separate database (too complex), full schema duplication (violates DRY), and a middleware translation layer (over-engineered),

**to achieve** seamless bidirectional data flow between Iris and Scenia with standard Iris element/relationship patterns,

**accepting that** Scenia entities share the elements table which may need element_type-based filtering.

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| Schema Mapping | Scenia entities stored as typed Iris elements | [SPEC-104-A](./specs/SPEC-104-A-Scenia-Data-Layer.md) |
| Scenia-specific Tables | Timeline settings, versions, asset categories, app statuses | [SPEC-104-A](./specs/SPEC-104-A-Scenia-Data-Layer.md) |
| Bulk Data API | Atomic read/write for Scenia's getAppData/saveAppData pattern | [SPEC-104-A](./specs/SPEC-104-A-Scenia-Data-Layer.md) |
| Extension Gating | All routes gated on scenia extension being enabled | [SPEC-104-A](./specs/SPEC-104-A-Scenia-Data-Layer.md) |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Extends | ADR-103 | Extensions Framework | Scenia is an extension managed by the registry |
| Relates To | ADR-004 | Backend Stack | Follows FastAPI module patterns |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-104-A | Scenia Data Layer | Technical Specification | [specs/SPEC-104-A-Scenia-Data-Layer.md](./specs/SPEC-104-A-Scenia-Data-Layer.md) |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-03-25 |
| Approved | Chris Barlow | 2026-03-25 |
