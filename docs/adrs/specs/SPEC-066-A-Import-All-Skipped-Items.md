# SPEC-066-A: Import All Skipped Items, Smart Tab Fix, Import Change Summary

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-066-A |
| **ADR** | ADR-066 |
| **Date** | 2026-03-03 |

---

## 1. Smart Tab Fix

**File:** `frontend/src/routes/models/[id]/+page.svelte`

Reset `userSelectedTab = false` when model ID changes so the smart default logic re-evaluates.

## 2. Import Change Summary

**Files:** `backend/app/entities/service.py`, `backend/app/models_crud/service.py`, `backend/app/import_sparx/service.py`

- Add `change_summary: str | None = None` to `create_entity()` and `create_model()` signatures
- Include `change_summary` column in version INSERT SQL
- Pass from import: `"Imported from SparxEA ({type})"` for entities/models/diagrams

## 3. Migration m015: model_relationships Table

**File:** `backend/app/migrations/m015_model_relationships.py`

```sql
CREATE TABLE model_relationships (
    id TEXT PRIMARY KEY,
    source_model_id TEXT NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    target_model_id TEXT NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL,
    label TEXT,
    description TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(source_model_id, target_model_id, relationship_type)
)
```

## 4. Model Relationships Service + Router

**Files:** `backend/app/model_relationships/service.py`, `backend/app/model_relationships/router.py`

- CRUD: create, list (by model_id), delete
- API: POST/GET `/api/models/{id}/relationships`, DELETE `/api/model-relationships/{id}`

## 5. Mapper Changes

**File:** `backend/app/import_sparx/mapper.py`

- Move Note→`note`, Boundary→`boundary` from skip to OBJECT_TYPE_MAP
- Move NoteLink/Notelink→`note_link` from skip to CONNECTOR_TYPE_MAP
- SKIP_OBJECT_TYPES becomes `{"Text", "UMLDiagram", "Constraint"}`
- SKIP_CONNECTOR_TYPES becomes empty set

## 6. Import Service Changes

**File:** `backend/app/import_sparx/service.py`

- Remove self-reference guard (line 238-240)
- Build `element_to_package` reverse map for Package→Package dependency import
- Add section 4b: create model_relationships for Package→Package connectors
- Add `model_relationships_created` to ImportSummary
- Pass `change_summary` to all create calls

## 7. Canvas Self-Ref Guard Removal

**File:** `backend/app/models_crud/service.py` (line 305)

Change `source_entity != target_entity` guard to allow self-references.

## 8. Frontend Components

### NoteNode (`frontend/src/lib/canvas/nodes/NoteNode.svelte`)
Yellow/cream background, folded corner, DOMPurify-sanitized description, Handle pattern.

### BoundaryNode (`frontend/src/lib/canvas/nodes/BoundaryNode.svelte`)
Dashed border, header label, transparent background, Handle pattern.

### NoteLinkEdge (`frontend/src/lib/canvas/edges/NoteLinkEdge.svelte`)
Dotted line (stroke-dasharray: 2 2), no arrowhead.

### SelfLoopEdge (`frontend/src/lib/canvas/edges/SelfLoopEdge.svelte`)
Cubic bezier loop from right side, curves up and returns to top.

### Type Registrations
- `frontend/src/lib/canvas/nodes/index.ts`: Add `note`, `boundary`
- `frontend/src/lib/canvas/edges/index.ts`: Add `note_link`, `self_loop`
- `frontend/src/lib/types/canvas.ts`: Add types to unions and metadata arrays

## 9. Model Relationships Tab

**File:** `frontend/src/routes/models/[id]/+page.svelte`

- Extend activeTab union with `'relationships'`
- Add "Relationships" tab button
- Fetch/display model relationships with type badges and delete actions

## 10. Import Self-Loop Edges

**File:** `backend/app/import_sparx/service.py`

When `source_node == target_node` in diagram edge building, emit `type: "self_loop"` with `sourceHandle: "right"`, `targetHandle: "top"`.

---

## Tests

### Backend (~14 new tests)

| Test | Category |
|------|----------|
| test_create_model_relationship | model_relationships |
| test_list_model_relationships | model_relationships |
| test_delete_model_relationship | model_relationships |
| test_duplicate_model_relationship | model_relationships |
| test_model_relationship_cascade_delete | model_relationships |
| test_map_note_type | mapper |
| test_map_boundary_type | mapper |
| test_map_notelink_type | mapper |
| test_import_self_referencing_connector | import |
| test_import_package_dependencies | import |
| test_import_notes_as_entities | import |
| test_import_notelinks_as_relationships | import |
| test_import_change_summary_entity | import |
| test_import_change_summary_model | import |
