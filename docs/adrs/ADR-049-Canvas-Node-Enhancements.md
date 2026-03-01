# ADR-049: Canvas Node Enhancements

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-049 |
| **Initiative** | Canvas Node Enhancements (WP-5, WP-8) |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris model canvas where node labels and descriptions can become stale after entity metadata is updated via the entity detail page or the entity edit dialog (WP-5), and where there is no visual mechanism to reference one model from within another model's canvas to represent hierarchical or compositional architecture views (WP-8),

**facing** the need for canvas nodes to stay synchronised with their backing entities and for users to express model-in-model composition on the canvas,

**we decided for** (WP-5) a `refreshNodeDescriptions()` function that takes the current node array, extracts all linked entity IDs, fetches their current metadata from the entity API via `Promise.all` for parallel execution, and updates each node's `label` and `description` fields to match the entity's current name and description, called on canvas load and after entity edit; (WP-8) a new `ModelRefNode.svelte` component with a stacked-squares visual treatment (a layered rectangle icon) distinguishing it from entity nodes, registered as the `modelref` node type in the @xyflow/svelte node type registry, that displays the referenced model's name and links to its canvas view,

**and neglected** WebSocket-based real-time entity update subscriptions (over-engineered for the current single-user workflow; polling on load is sufficient), embedding the full referenced model's canvas inline as a nested @xyflow/svelte instance (massive complexity and performance cost), and using a generic link node type for model references (loses the semantic distinction between entity nodes and model references),

**to achieve** accurate node metadata on the canvas that reflects the latest entity state without manual intervention, and a dedicated model-in-model composition primitive that enables hierarchical architecture views with clear visual differentiation,

**accepting that** `refreshNodeDescriptions()` fires N parallel API calls (one per linked entity) which is acceptable for typical model sizes (tens to low hundreds of nodes), the refresh only runs on canvas load and after explicit entity edits (not in real-time), and `ModelRefNode` only links to the referenced model and does not display a preview of its contents.

---

## Options Considered

### Option 1: Parallel Entity Fetch + Dedicated ModelRefNode (Selected)

**Pros:**
- `Promise.all` keeps refresh fast even with many nodes
- Runs automatically on canvas load; no user action required
- `ModelRefNode` provides clear visual semantics for model references
- Registered as a distinct node type, enabling type-specific behaviour

**Cons:**
- N API calls on canvas load (mitigated by parallelism)
- Stacked-squares visual is custom SVG that must be maintained

**Why selected:** Simple, effective synchronisation for entity metadata, and a clean architectural primitive for model composition.

### Option 2: WebSocket Real-Time Entity Sync (Rejected)

**Pros:**
- Instant updates when entity metadata changes

**Cons:**
- Requires WebSocket infrastructure (server and client)
- Over-engineered for current use case where edits are infrequent
- Adds connection management complexity

**Why rejected:** Premature complexity; on-load refresh covers the use case adequately.

### Option 3: Nested Canvas for Model-in-Model (Rejected)

**Pros:**
- Rich preview of the referenced model's contents

**Cons:**
- Nesting @xyflow/svelte instances is unsupported and causes context conflicts
- Severe performance degradation with multiple nested canvases
- Interaction conflicts between parent and child canvas events

**Why rejected:** Technically infeasible with @xyflow/svelte's context-based architecture.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-03-01 | Accepted | Add node description sync and ModelRefNode | 6 months | 2026-09-01 |

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
| Depends On | ADR-020 | Entity Persistence from Model Editor | Entities fetched via entity API for description sync |
| Depends On | ADR-014 | Canvas UX Parity | Canvas node types extended with modelref |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
