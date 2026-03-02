# ADR-055: Model Hierarchy

## Proposal: Add Parent-Child Hierarchy to Models

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-055 |
| **Initiative** | SparxEA Integration |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-02 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** importing SparxEA enterprise architecture models which use deep package hierarchies to organise diagrams,

**facing** the limitation that Iris models are currently flat with no parent/child relationships, making it impossible to represent the hierarchical structure of imported EA repositories,

**we decided for** adding a `parent_model_id` column to the models table with API endpoints for hierarchy retrieval, ancestor breadcrumbs, child listing, and parent assignment with cycle validation,

**and neglected** using a separate hierarchy table (more complex, no clear benefit for tree depth), materialised path encoding (harder to maintain on reparent), and nested set model (complex updates on insert/move),

**to achieve** hierarchical model organisation that supports SparxEA package import, tree navigation in the UI, and breadcrumb-based wayfinding,

**accepting that** existing models will default to root-level (NULL parent), the hierarchy is advisory (no cascading deletes), and deep hierarchies may require pagination in future.

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Enables | ADR-059 | SparxEA Import | Package hierarchy maps to model hierarchy |
| Relates To | ADR-003 | Entity Domain Model | Models table schema |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-055-A | Model Hierarchy Schema | Technical Specification | [specs/SPEC-055-A-Model-Hierarchy-Schema.md](./specs/SPEC-055-A-Model-Hierarchy-Schema.md) |
| SPEC-055-B | Model Hierarchy API | Technical Specification | [specs/SPEC-055-B-Model-Hierarchy-API.md](./specs/SPEC-055-B-Model-Hierarchy-API.md) |

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Architecture Team | 2026-03-02 | Approved | Implementation | 6 months | 2026-09-02 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Approved | Architecture Team | 2026-03-02 |
