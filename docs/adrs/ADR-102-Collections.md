# ADR-102: Collections

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-102 |
| **Initiative** | Collections |
| **Proposed By** | Engineering |
| **Date** | 2026-03-24 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris architecture modeling tool, where Sets serve as the primary organizational unit for grouping diagrams and elements,

**facing** the need to organize related Sets into higher-level groupings for filtering, navigation, and multi-set AI context — particularly for large organisations with many Sets,

**we decided for** adding a Collections entity as an optional superset of Sets, with its own CRUD, thumbnails, navigation, dashboard presence, and multi-set AI Q&A support,

**and neglected** nested Sets (adds recursive complexity with minimal UX benefit), tag-based grouping (too loosely coupled, no first-class entity), and folder hierarchies (over-engineered for a single level of grouping),

**to achieve** a clean organisational hierarchy (Collection → Set → Diagrams/Elements) that enables cross-set filtering, collection-scoped AI queries, and better navigation for users managing multiple Sets,

**accepting that** this adds a new database table and FK relationship, and that Collections are optional — Sets can exist without belonging to a Collection.

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| Collections CRUD | Create, read, update, soft-delete collections with thumbnails | [SPEC-102-A](./specs/SPEC-102-A-Collections.md) |
| Set-Collection linking | Optional collection_id FK on sets table | [SPEC-102-A](./specs/SPEC-102-A-Collections.md) |
| Multi-set AI context | Ask AI across multiple sets in a collection | [SPEC-102-A](./specs/SPEC-102-A-Collections.md) |
| Collection filtering | Filter Elements and Diagrams pages by collection | [SPEC-102-A](./specs/SPEC-102-A-Collections.md) |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Extends | ADR-060 | Sets Batch Operations | Sets are the child entity |
| Extends | ADR-093 | AI Model Management | Multi-set AI context |
| Relates To | ADR-062 | Persistent Set Selection | Active collection store mirrors this pattern |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-102-A | Collections | Technical Specification | [specs/SPEC-102-A-Collections.md](./specs/SPEC-102-A-Collections.md) |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Approved | Engineering | 2026-03-24 |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
