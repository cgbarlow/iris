# ADR-040: Roadmap Model Type

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-040 |
| **Initiative** | Roadmap Model Type (WP-12) |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris architecture modelling tool where users need to create roadmap-style models to plan and communicate architectural evolution over time,

**facing** the limitation that the current model type options (Simple, Component, Sequence, UML, ArchiMate) do not include a dedicated roadmap type, forcing users to repurpose other model types for roadmap planning,

**we decided for** adding a new `roadmap` model type to the frontend model creation dialog, model type filter dropdown, and model detail page canvas type mapping, where roadmap models use the existing simple canvas view,

**and neglected** creating a dedicated roadmap-specific canvas renderer (premature — the simple canvas provides sufficient node and edge capabilities for initial roadmap modelling), and adding backend schema changes (the backend already accepts arbitrary model_type strings),

**to achieve** a first-class roadmap model type that users can create, filter, and view using the established simple canvas infrastructure,

**accepting that** roadmap models share the same canvas rendering as simple and component models, which may be enhanced with roadmap-specific features in a future iteration.

---

## Options Considered

### Option 1: Add Roadmap as Frontend Model Type with Simple Canvas (Selected)

**Pros:**
- Minimal change — only three frontend files modified
- Reuses proven simple canvas infrastructure
- No backend changes required (backend is model_type agnostic)
- Users can immediately create and work with roadmap models

**Cons:**
- No roadmap-specific visual treatment (e.g., timeline lanes, milestone markers)
- Shares canvas renderer with simple and component types

**Why selected:** Provides immediate value with minimal risk. Roadmap-specific canvas features can be added incrementally in future work packages.

### Option 2: Build a Dedicated Roadmap Canvas (Rejected)

**Pros:**
- Purpose-built timeline/lane visualisation
- Distinct visual identity for roadmap models

**Cons:**
- Significant development effort for a new canvas type
- Delays delivery of the roadmap model type
- May over-engineer before user needs are fully understood

**Why rejected:** Premature optimisation. The simple canvas is sufficient for initial roadmap modelling. A dedicated canvas can be pursued once usage patterns are established.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-03-01 | Accepted | Add roadmap model type to frontend | 6 months | 2026-09-01 |

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
| Depends On | ADR-011 | Canvas Integration and Testing Strategy | Roadmap uses the simple canvas view established here |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-040-A | Roadmap Model Type Implementation | Technical Specification | [specs/SPEC-040-A-Roadmap-Model-Type.md](specs/SPEC-040-A-Roadmap-Model-Type.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
