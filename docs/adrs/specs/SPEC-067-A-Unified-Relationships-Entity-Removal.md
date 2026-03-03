# SPEC-067-A: Unified Relationship Management & Entity Removal from Canvas

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-067-A |
| **ADR** | ADR-067 |
| **Date** | 2026-03-03 |

---

## 1. Backend: Auto-create model_relationships from canvas edges

**File:** `backend/app/models_crud/service.py` — `update_model()`

After existing entity relationship auto-create block (~line 328):
- Build `node_model_map: dict[str, str]` from nodes with `data.linkedModelId`
- For each edge where both source/target map to a `linkedModelId`, check if `model_relationships` row exists
- If not, call `create_model_relationship()` with relationship_type from edge data
- Wrap in try/except — model save must never fail from this

## 2. Frontend: Canvas modelref-to-modelref connections

**File:** `frontend/src/routes/models/[id]/+page.svelte`

In `handleRelationshipSave()`, after existing entity relationship block, add `else if` for `linkedModelId`:
- Check `sourceNode?.data?.linkedModelId && targetNode?.data?.linkedModelId`
- Call `POST /api/models/{model.id}/relationships`

**File:** `frontend/src/lib/types/canvas.ts`

Add optional `modelRelationshipId?: string` to `CanvasEdgeData`.

## 3. Relationships Tab: Add Entity Relationship

**File:** `frontend/src/routes/models/[id]/+page.svelte`

Flow: EntityPicker (source) → EntityPicker (target) → RelationshipDialog → POST /api/relationships → "Add to canvas?" prompt

## 4. Relationships Tab: Add Model Relationship

**File:** `frontend/src/routes/models/[id]/+page.svelte`

Flow: ModelPicker (target selected) → RelationshipDialog → POST /api/models/{id}/relationships → "Add to canvas?" prompt

## 5. "Add to Canvas?" Prompt

For entity relationships: check if source/target entities already have nodes on canvas; if not, create nodes at open positions; add edge between them.

For model relationships: only add target model as modelref node (if not already present). No edge drawn — documented limitation.

## 6. EntityPicker/ModelPicker Title Props

**Files:** `frontend/src/lib/components/EntityPicker.svelte`, `frontend/src/lib/components/ModelPicker.svelte`

Add optional `title?: string` and `subtitle?: string` props with current strings as defaults.

## 7. Backend: Cascade Entity Deletion

**File:** `backend/app/entities/service.py` — new `cascade_delete_entity()`

1. Soft-delete the entity (reuse `soft_delete_entity`)
2. Soft-delete all relationships where entity is source or target
3. Find all models whose canvas JSON contains the entity ID
4. For each model: parse canvas data, remove matching nodes + connected edges, save updated canvas

**File:** `backend/app/entities/router.py`

Add `cascade: bool = False` query param to DELETE endpoint. When True, call `cascade_delete_entity()`.

## 8. Frontend: Node Delete Button + Dialog

**File:** `frontend/src/lib/components/NodeDeleteDialog.svelte` (new)

Two options:
1. "Remove from this model" — removes node + edges from canvas only
2. "Delete entity and all relationships" — calls DELETE /api/entities/{id}?cascade=true (only for entity nodes)

**File:** `frontend/src/routes/models/[id]/+page.svelte`

- "Remove" button in canvas toolbar when node selected in edit mode
- Keyboard Delete/Backspace opens dialog instead of direct removal
- `handleCascadeDeleteEntity()` handler

---

## Tests

### Backend (~6 new tests)

| Test | File |
|------|------|
| test_auto_create_model_relationship_on_canvas_save | test_model_relationships.py |
| test_auto_create_model_relationship_no_duplicate | test_model_relationships.py |
| test_cascade_delete_removes_from_model_canvas | test_entities/test_cascade_delete.py |
| test_cascade_delete_soft_deletes_relationships | test_entities/test_cascade_delete.py |
| test_cascade_delete_entity_marked_deleted | test_entities/test_cascade_delete.py |
| test_simple_delete_does_not_cascade | test_entities/test_cascade_delete.py |
