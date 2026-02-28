# ADR-020: Entity Persistence from Model Editor

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-020 |
| **Initiative** | Entity Persistence from Model Editor |
| **Proposed By** | Architecture Team |
| **Date** | 2026-02-28 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris model editor, where "Add Entity" creates a local-only canvas node without an `entityId`, meaning entities created in the model editor do not appear in the global entities list and are not persisted as first-class domain objects,

**facing** the need for entities to be consistently discoverable, searchable, and referenceable regardless of where they were created, so that the entities list, cross-references, and entity statistics reflect the full architectural landscape,

**we decided for** persisting entities via `POST /api/entities` before adding them to the canvas, so that `handleAddEntity()` first creates a backend entity record and then adds the canvas node with the returned `entityId`, making model-editor-created entities identical to entities created from the entities list page,

**and neglected** keeping entities as canvas-local data that only exist within the model's `data` JSON (which avoids an extra API call but leaves entities invisible outside the model), and batch-persisting entities at canvas save time (which defers persistence but introduces complexity around partial failures and orphan nodes),

**to achieve** a unified entity model where every entity on every canvas is a first-class, versioned, searchable domain object with a stable identity, ensuring consistency between the model editor and the global entities list,

**accepting that** adding an entity in the model editor now requires a network round-trip before the node appears on the canvas, and that if the API call fails the node will not be added (with an error message shown to the user).

---

## Options Considered

### Option 1: Persist Entity on Creation (Selected)

**Pros:**
- Entity is immediately visible in the global entities list
- Entity has a stable ID for cross-references, statistics, and search
- Consistent with entities created from the entities list page
- Simple, synchronous flow: create entity, then add node

**Cons:**
- Adds a network round-trip before the node appears on the canvas
- If the API call fails, the user sees an error instead of a node

### Option 2: Keep Entities as Canvas-Local Data (Rejected)

**Pros:**
- No network call required; instant node creation
- Simpler implementation (no API integration)

**Cons:**
- Entities are invisible outside the model
- No stable entity ID for cross-references or search
- Creates two classes of entities: "real" (from entities list) and "ghost" (from model editor)

**Why rejected:** Having entities that exist only within a model's canvas data fundamentally breaks the domain model. Entities should be first-class objects regardless of where they were created.

### Option 3: Batch-Persist at Canvas Save Time (Rejected)

**Pros:**
- Defers API calls until the user explicitly saves
- Allows creating multiple entities without multiple round-trips

**Cons:**
- Complex partial-failure handling (some entities persist, others fail)
- Orphan canvas nodes if batch creation partially fails
- Entity IDs are not available until save, complicating cross-references during editing

**Why rejected:** The complexity of handling partial failures and the delayed availability of entity IDs make this approach fragile and harder to reason about.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-28 | Accepted | Implement entity persistence in model editor | 6 months | 2026-08-28 |

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
| Depends On | ADR-011 | Canvas Integration and Testing Strategy | Canvas node/entity integration patterns |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-020-A | Entity Persistence | Technical Specification | [specs/SPEC-020-A-Entity-Persistence.md](specs/SPEC-020-A-Entity-Persistence.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
