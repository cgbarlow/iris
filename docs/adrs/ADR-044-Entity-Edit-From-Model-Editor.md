# ADR-044: Entity Edit from Model Editor

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-044 |
| **Initiative** | Entity Edit from Model Editor (WP-15) |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris model editor where users can create new entities and link existing entities to canvas nodes, but cannot edit the underlying entity data (name, type, description) once a node is placed on the canvas without navigating away to the entity detail page,

**facing** the requirement that users working in the model editor need a streamlined workflow to update entity metadata directly from the canvas without losing their editing context or unsaved canvas changes,

**we decided for** adding an "Edit Entity" button to the canvas toolbar's Edit group that appears when a linked entity node is selected in edit mode, which fetches the entity from `GET /api/entities/{entityId}`, opens the existing `EntityDialog` in edit mode with pre-filled data, and on save issues `PUT /api/entities/{entityId}` with an `If-Match` header for optimistic concurrency before updating the canvas node's label, type, and description in place,

**and neglected** inline editing directly on canvas nodes (would require complex custom node components with editable fields and conflict with @xyflow/svelte's node rendering model), opening the entity detail page in a new tab or modal (breaks editing context and risks stale canvas state), and a separate dedicated edit dialog component (duplicates the existing `EntityDialog` which already supports both create and edit modes),

**to achieve** in-context entity editing from the model editor that reuses the existing `EntityDialog` component, maintains optimistic concurrency via `If-Match` headers, and immediately reflects entity changes on the canvas without requiring a full page reload,

**accepting that** the entity edit only updates name, type, and description (not tags or relationships which require the full entity detail page), and that saving the entity is independent from saving the canvas layout (the entity is persisted immediately via API, while the canvas node update marks the canvas as dirty for a separate save).

---

## Options Considered

### Option 1: Toolbar Button with Existing EntityDialog (Selected)

**Pros:**
- Reuses the existing `EntityDialog` component (DRY principle)
- Consistent UX with entity creation flow
- Maintains optimistic concurrency via `If-Match` headers
- Canvas node updates immediately reflect the edit
- No new components needed

**Cons:**
- Requires adding `onnodeselect` callback to canvas components
- Entity save and canvas save are separate operations

**Why selected:** Minimal implementation complexity, maximum code reuse, and consistent user experience with existing patterns.

### Option 2: Inline Node Editing (Rejected)

**Pros:**
- Most direct editing experience
- No dialog overlay

**Cons:**
- Conflicts with @xyflow/svelte node rendering model
- Would require custom editable node components for all entity types
- Complex focus management between canvas and inline editors
- No room for entity type selection in a small node

**Why rejected:** Too complex for the benefit gained; @xyflow/svelte nodes are not designed for inline editing.

### Option 3: Navigate to Entity Detail Page (Rejected)

**Pros:**
- Full entity editing capabilities (tags, relationships, etc.)

**Cons:**
- Breaks editing context completely
- User loses unsaved canvas changes
- Disorienting navigation flow

**Why rejected:** Destroys the in-context editing workflow that users expect.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-03-01 | Accepted | Add Edit Entity button and reuse EntityDialog | 6 months | 2026-09-01 |

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
| Depends On | ADR-020 | Entity Persistence from Model Editor | Entities are created as first-class API entities |
| Depends On | ADR-030 | Model Canvas Toolbar Layout | Edit Entity button placed in the Edit group |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-044-A | Entity Edit from Model Editor | Technical Specification | [specs/SPEC-044-A-Entity-Edit-From-Model-Editor.md](specs/SPEC-044-A-Entity-Edit-From-Model-Editor.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
