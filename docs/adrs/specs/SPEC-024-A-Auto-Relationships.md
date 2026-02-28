# SPEC-024-A: Auto-Relationships Implementation

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-024-A |
| **ADR Reference** | [ADR-024: Entity Relationship Auto-Creation](../ADR-024-Entity-Relationship-Auto-Creation.md) |
| **Date** | 2026-02-28 |
| **Status** | Active |

---

## Overview

This specification covers the automatic creation of entity relationships from canvas edges during model save, improved empty state messaging for the relationships tab, and reordered entity detail tabs for better information hierarchy.

---

## A. Backend: Auto-Create Relationships on Model Save

### Location

`backend/app/models_crud/service.py` — `update_model()` function.

### Behaviour

After the model version is saved and the search index is updated, the function parses the saved model data to identify edges between entity-backed nodes and creates relationships for any pairs not already linked.

### Algorithm

1. Extract `nodes` and `edges` lists from the model `data` dict.
2. Build a mapping of `node.id` to `node.data.entityId` for all nodes that have an `entityId`.
3. For each edge, resolve `source` and `target` to entity IDs via the node mapping.
4. Skip edges where source or target has no entity ID, or where source equals target (self-referencing).
5. Query the `relationships` table for an existing non-deleted relationship with the same `source_entity_id` and `target_entity_id`.
6. If no existing relationship is found, create one via `create_relationship()` with:
   - `relationship_type`: from `edge.data.relationshipType` if present, otherwise `"uses"`
   - `label`: `None`
   - `description`: `None`
   - `data`: `{}`
   - `created_by`: the `updated_by` user from the model save

### Error Handling

The entire auto-creation block is wrapped in `try/except Exception: pass`. Relationship creation failures must never prevent a successful model save.

### Import

Add to `service.py`:
```python
from app.relationships.service import create_relationship
```

---

## B. Frontend: Entity Detail Tab Reordering

### Location

`frontend/src/routes/entities/[id]/+page.svelte`

### Tab Order Change

| Before | After |
|--------|-------|
| Details | Details |
| Version History | Used In Models |
| Relationships | Relationships |
| Used In Models | Version History |

Reorder both the tab buttons in the `role="tablist"` container and the corresponding `{#if}` / `{:else if}` content blocks in the tab panel.

---

## C. Frontend: Relationships Empty State

### Location

`frontend/src/routes/entities/[id]/+page.svelte` — relationships tab empty state.

### Change

From:
```
No relationships found.
```

To:
```
No relationships yet. Relationships are created automatically when entities are connected by edges in a model canvas.
```

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Saving a model with edges between entity nodes creates relationships | Create two entities, add both to a canvas, draw an edge, save. Check entity relationships tab shows the relationship. |
| Duplicate relationships are not created | Save the same model again without changes. Verify no duplicate relationship appears. |
| Self-referencing edges are skipped | Draw an edge from a node back to itself. Save. Verify no relationship is created. |
| Relationship type comes from edge data | Draw an edge with a custom relationship type. Save. Verify the relationship uses that type. |
| Default relationship type is "uses" | Draw a plain edge with no type data. Save. Verify the relationship type is "uses". |
| Model save succeeds even if relationship creation fails | Verify that invalid entity IDs in edge data do not cause model save to fail. |
| Entity tabs are reordered | Open entity detail. Verify tab order: Details, Used In Models, Relationships, Version History. |
| Empty state message is descriptive | Open entity detail with no relationships. Verify the improved empty state text. |

---

*This specification implements [ADR-024](../ADR-024-Entity-Relationship-Auto-Creation.md).*
