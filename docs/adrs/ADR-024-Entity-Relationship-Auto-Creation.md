# ADR-024: Entity Relationship Auto-Creation

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-024 |
| **Initiative** | Entity Relationships Tab UX and Auto-Create from Canvas Edges |
| **Proposed By** | Architecture Team |
| **Date** | 2026-02-28 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris entity relationships tab being persistently empty because relationships must be manually created through the API, while users are already connecting entities visually by drawing edges between nodes on the model canvas,

**facing** the disconnect between the visual representation of entity connections on canvases and the underlying relationship data model, where users expect that connecting two entities on a canvas would naturally establish a relationship between them,

**we decided for** automatically creating entity relationships in the database whenever a model is saved with edges that connect nodes backed by distinct entities. When `update_model()` processes a save, it parses the model data for edges between entity-backed nodes and creates relationships (type defaults to "uses", overridable via edge data) for any pair not already linked. The operation is wrapped in a try/except so that relationship auto-creation failures never prevent a model save. Additionally, the entity detail page tab order is reordered to prioritise discovery (Details, Used In Models, Relationships, Version History) and the relationships empty state message is improved to explain how relationships are created.

**and neglected** requiring users to manually create relationships through a separate UI, real-time relationship creation on each edge draw (before save), and bidirectional relationship creation (creating both A-to-B and B-to-A),

**to achieve** automatic population of the entity relationships tab from existing canvas work, reducing friction for users who model visually and expect the relationship data to reflect their diagrams,

**accepting that** relationships are only created on model save (not in real-time), only in the source-to-target direction of the edge, deleted edges do not remove relationships, and the default relationship type is "uses" unless edge data specifies otherwise.

---

## Options Considered

### Option 1: Auto-Create on Model Save (Selected)

**Pros:**
- Leverages existing save flow, minimal new code
- Batch processing avoids per-edge API overhead
- Failure-safe: wrapped in try/except, never blocks model save
- Idempotent: checks for existing relationships before creating

**Cons:**
- Relationships only appear after save, not immediately on edge draw
- Does not remove relationships when edges are deleted

**Why selected:** Simplest approach that solves the core problem. Users save models frequently, so the delay is negligible. The idempotent check prevents duplicates.

### Option 2: Real-Time Creation on Edge Draw (Rejected)

**Pros:**
- Immediate feedback in the relationships tab

**Cons:**
- Requires new WebSocket or API call per edge creation
- Edge may be drawn and deleted before save (transient edges)
- More complex error handling mid-canvas interaction

**Why rejected:** Adds significant complexity for minimal UX benefit. Users do not typically check the relationships tab while actively editing a canvas.

### Option 3: Manual Relationship Creation Only (Rejected)

**Pros:**
- No code changes needed

**Cons:**
- Relationships tab remains perpetually empty for most users
- Duplicates effort: users draw edges on canvas then must separately create relationships

**Why rejected:** This is the current state and the root cause of the problem being solved.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-28 | Accepted | Implement auto-creation and UX improvements | 6 months | 2026-08-28 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Architecture Team | 2026-02-28 |
| Accepted | Project Lead | 2026-02-28 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Depends On | ADR-003 | Architectural Vision | Uses existing entity and relationship domain models |
| Depends On | ADR-011 | Canvas Integration and Testing Strategy | Extends model save flow with relationship side-effects |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-024-A | Auto-Relationships Implementation | Technical Specification | [specs/SPEC-024-A-Auto-Relationships.md](specs/SPEC-024-A-Auto-Relationships.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
