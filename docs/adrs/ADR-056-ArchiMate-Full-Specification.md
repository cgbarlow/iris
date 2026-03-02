# ADR-056: ArchiMate Full Specification

## Proposal: Expand ArchiMate Support to Full 6-Layer Specification

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-056 |
| **Initiative** | ArchiMate Full Specification |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-02 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris ArchiMate canvas support, which currently covers 11 entity types across 3 layers (business, application, technology) with 8 relationship types,

**facing** the limitation that the ArchiMate 3.2 specification defines approximately 45 entity types across 6 layers (business, application, technology, motivation, strategy, implementation & migration) with 11 relationship types, and users need the full specification to model enterprise architectures accurately,

**we decided for** expanding the frontend type registry to cover all 6 ArchiMate layers with ~45 entity types and 11 relationship types, adding node registry entries and layer-specific CSS styling for each new layer,

**and neglected** implementing a partial expansion limited to only the most-used types (would still leave gaps), and backend schema changes (unnecessary since entity_type is free-form TEXT),

**to achieve** comprehensive ArchiMate 3.2 specification coverage enabling users to model motivation, strategy, and implementation & migration elements alongside the existing business, application, and technology layers,

**accepting that** this is a frontend-only change with no backend migration needed, and the expanded type list increases the entity type picker size which may need UX refinement in future iterations.

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Extends | ADR-054 | ArchiMate Seed Data Node Type Mapping | Builds on existing ArchiMate support |
| Relates To | ADR-011 | Canvas Integration and Testing Strategy | Canvas node/edge type registry |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-056-A | ArchiMate Type Registry Expansion | Technical Specification | [specs/SPEC-056-A-ArchiMate-Type-Registry.md](./specs/SPEC-056-A-ArchiMate-Type-Registry.md) |

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Architecture Team | 2026-03-02 | Accepted | Implementation | 6 months | 2026-09-02 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Accepted | Architecture Team | 2026-03-02 |
