# ADR-054: ArchiMate Seed Data Node Type Mapping

## Proposal: Fix Seed Enterprise Model to Use ArchiMate Node Types

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-054 |
| **Initiative** | ArchiMate Seed Data Fix |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-01 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris Enterprise View seed model (model_type="archimate"), which is rendered in edit mode using FullViewCanvas with the archimateNodeTypes registry,

**facing** the bug that entity boxes disappear and only text labels are visible in ArchiMate edit view, because nodes use Simple View types ("actor", "component", "service", etc.) which are not in the archimateNodeTypes registry, causing @xyflow/svelte to render a text-only fallback,

**we decided for** fixing the seed data to use correct ArchiMate node types (business_actor, application_component, etc.) and including the required "layer" and "archimateType" fields in node data objects so ArchimateNode.svelte renders correctly with coloured layer badges,

**and neglected** adding fallback rendering in FullViewCanvas for unrecognised types (would mask data errors), and adding Simple View types to the archimateNodeTypes registry (would bypass the ArchiMate visual system),

**to achieve** correct rendering of the Enterprise View model with proper ArchiMate visual styling including layer-coloured borders and badges,

**accepting that** this changes the seed data contract and existing databases with the old seed data will retain the broken rendering until the seed data is re-created (idempotent seed skips if data exists).

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Relates To | ADR-045 | Example Iris Architecture Models | Seed data definition |
| Relates To | ADR-011 | Canvas Integration and Testing Strategy | ArchiMate node types |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-054-A | ArchiMate Seed Data Fix | Technical Specification | [specs/SPEC-054-A-ArchiMate-Seed-Data-Fix.md](./specs/SPEC-054-A-ArchiMate-Seed-Data-Fix.md) |

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Architecture Team | 2026-03-01 | Approved | Implementation | 6 months | 2026-09-01 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Approved | Architecture Team | 2026-03-01 |
