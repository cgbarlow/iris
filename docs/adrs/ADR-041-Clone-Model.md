# ADR-041: Clone Model

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-041 |
| **Initiative** | Clone Model (WP-14) |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris model management workflow where users frequently create models that are structurally similar to existing ones (e.g., variants of the same architecture, iterations of a design), but must currently start from scratch each time by creating a blank model and manually recreating all entities and relationships on the canvas,

**facing** the need for a quick way to duplicate an existing model as a starting point for a new design, preserving the canvas layout (node positions, edges, sequence data) so users can iterate without re-doing significant manual work,

**we decided for** adding a "Clone" button to the model detail page toolbar that opens the existing `ModelDialog` in create mode with pre-filled fields (name suffixed with "(Copy)", same description and model type), and on save POSTs to the existing `POST /api/models` endpoint with the original model's `data` (canvas placements) included, then navigates to the newly created model,

**and neglected** a backend-specific clone endpoint (the existing POST /api/models already accepts a `data` field, making a dedicated endpoint unnecessary), and a bulk clone feature (single model clone covers the primary use case),

**to achieve** a one-click workflow for duplicating models with their full canvas layout, reducing the effort to create model variants from minutes of manual reconstruction to a single button click,

**accepting that** the clone creates an independent copy with no link back to the original model, and that entity references within the canvas data point to the same underlying entities (entities are not duplicated, only the canvas placement data is copied).

---

## Options Considered

### Option 1: Frontend Clone via Existing POST /api/models (Selected)

**Pros:**
- No backend changes required — existing endpoint already accepts `data` field
- Reuses the existing `ModelDialog` component for name/description editing
- Simple, predictable behavior — user sees what they are creating before saving
- Consistent with existing model creation flow

**Cons:**
- Clone logic lives entirely in the frontend
- No server-side audit trail linking clone to original (only a change_summary note)

**Why selected:** The existing API already supports everything needed. Adding a backend endpoint would be over-engineering for a feature that is fundamentally "create a new model with pre-populated data."

### Option 2: Dedicated Backend Clone Endpoint (Rejected)

**Pros:**
- Server-side record of clone provenance
- Could deep-clone entities in the future

**Cons:**
- Requires new API endpoint, route, service method, and tests
- Over-engineered for the current requirement (canvas data copy only)
- Deep entity cloning is not desired (entities should be shared, not duplicated)

**Why rejected:** Unnecessary complexity when the existing POST endpoint handles the use case.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-03-01 | Accepted | Add Clone button to model detail page | 6 months | 2026-09-01 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Architecture Team | 2026-03-01 |
| Accepted | Project Lead | 2026-03-01 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Depends On | ADR-018 | Model Creation Navigation | Clone reuses the same POST + goto pattern |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-041-A | Clone Model | Technical Specification | [specs/SPEC-041-A-Clone-Model.md](specs/SPEC-041-A-Clone-Model.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
