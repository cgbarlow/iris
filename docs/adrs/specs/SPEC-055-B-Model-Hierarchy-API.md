# SPEC-055-B: Model Hierarchy API

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-055-B |
| **ADR** | [ADR-055](../ADR-055-Model-Hierarchy.md) |
| **Status** | Implemented |

## New Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/models/hierarchy?root_id=` | Full tree or subtree |
| GET | `/api/models/{id}/ancestors` | Breadcrumb chain (root first) |
| GET | `/api/models/{id}/children` | Direct children |
| PUT | `/api/models/{id}/parent` | Set/unset parent |

## Hierarchy Retrieval

`GET /api/models/hierarchy` returns `list[ModelHierarchyNode]` — a recursive tree structure. Optional `root_id` query param returns a subtree.

## Ancestor Chain

`GET /api/models/{id}/ancestors` returns ancestors from root to immediate parent (breadcrumb order).

## Set Parent

`PUT /api/models/{id}/parent` with body `{"parent_model_id": "..." | null}`.

- 400 if setting parent would create a cycle (self-reference or ancestor loop)
- 404 if model or parent not found

## Cycle Validation

`validate_no_cycle()` walks iteratively from proposed parent to root. If it encounters the model being reparented, a cycle would be created and the operation is rejected.

## Service Functions

- `get_model_hierarchy(db, root_id=None)` — fetches all models, builds in-memory tree
- `get_ancestors(db, model_id)` — walks parent chain upward
- `get_children(db, model_id)` — direct children query
- `set_model_parent(db, model_id, parent_model_id, updated_by)` — validates and updates
- `validate_no_cycle(db, model_id, proposed_parent_id)` — iterative ancestor walk

## Test Coverage

20 tests in `test_model_hierarchy.py`:
- Create with/without parent, get model includes parent_id
- Hierarchy: empty, flat, nested, subtree
- Ancestors: root (empty), deep chain
- Children: empty, multiple
- Set/unset parent, nonexistent model/parent
- Cycle prevention: self-reference, 2-node, 3-node cycles
- Deleted models excluded from hierarchy and children
