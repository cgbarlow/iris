# SPEC-063-A: Pagination Disabled Styling, Set Name Uniqueness Fix, Model Tree Explorer

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-063-A |
| **ADR** | [ADR-063](../ADR-063-Pagination-Set-Uniqueness-Tree-Explorer.md) |
| **Status** | Living |
| **Last Updated** | 2026-03-02 |

---

## 1. Pagination Disabled Styling

### Pagination.svelte (Prev/Next buttons)
- Add `disabled:opacity-50 disabled:cursor-not-allowed` to button class strings
- Matches pattern used elsewhere in codebase (e.g., sequence toolbar, canvas edit toolbar)

### Audit Log Page (inline pagination)
- Add same `disabled:opacity-50 disabled:cursor-not-allowed` to Previous/Next buttons
- Existing color change (`var(--color-muted)` when disabled) is retained

## 2. Soft-Deleted Set Name Uniqueness

### Migration m014_sets_partial_unique.py
1. Idempotent guard: check if `idx_sets_name_active` index already exists
2. Create `sets_new` table with identical schema but NO UNIQUE on `name`
3. Copy all data from `sets` to `sets_new`
4. Drop `sets` table
5. Rename `sets_new` to `sets`
6. Create `idx_sets_name` regular index on `name`
7. Create `idx_sets_name_active` partial unique index: `UNIQUE ON sets(name) WHERE is_deleted = 0`
8. Commit

### Behavior
- Active (non-deleted) sets: duplicate names still blocked by partial unique index
- Soft-deleted sets: names released for reuse by new active sets
- Multiple soft-deleted sets can share the same name

## 3. Set-Scoped Hierarchy API

### Backend Changes
- `get_model_hierarchy(db, root_id, set_id)`: when `set_id` provided, add `AND m.set_id = ?` to WHERE clause
- `GET /api/models/hierarchy?set_id=...`: new optional query parameter, passed to service

## 4. Model Detail Tree Sidebar

### State
- `sidebarOpen: boolean` — controls sidebar visibility
- `hierarchyTree: ModelHierarchyNode[]` — loaded tree data
- `hierarchyLoading: boolean` — loading indicator
- `treeSearchQuery: string` — search filter text
- `showCreateChildDialog: boolean` — child creation dialog
- `showParentPicker: boolean` — parent selection dialog

### Sidebar Layout
- Width: 280px, max-height: calc(100vh - 80px), overflow-y: auto
- Header: "Hierarchy" title, close button, "Add Child" button
- Search input: filters tree nodes
- Tree: `<ul role="tree">` with `TreeNode` components
- Positioned as flex sibling to main content

### Toggle Button
- Tree icon button next to model title `<h1>`
- `aria-label="Toggle hierarchy sidebar"`, `aria-pressed`
- On open: loads hierarchy if not yet loaded

### Navigation
- `TreeNode` renders `<a href="/models/{id}">` links
- SvelteKit handles client-side navigation
- Existing `$effect` on `page.params.id` triggers `loadModel()`
- If sidebar open and new model has different `set_id`, reload tree

### Add Child
- Button in sidebar header
- Opens `ModelDialog` in create mode
- On save: POST `/api/models` with `parent_model_id: model.id`, `set_id: model.set_id`
- Navigate to new model, reload tree

### Parent Management
- "Parent" field in overview `<dl>` grid
- Shows current parent name (linked) or "None — root model"
- "Change" button opens `ModelPicker`
- On select: PUT `/api/models/{id}/parent` with `{ parent_model_id: selectedId }`
- "Remove parent" option: PUT with `{ parent_model_id: null }`
- Backend cycle detection returns 400 — shown as error

## 5. Files Modified

| File | Type |
|------|------|
| `frontend/src/lib/components/Pagination.svelte` | Modified |
| `frontend/src/routes/admin/audit/+page.svelte` | Modified |
| `backend/app/migrations/m014_sets_partial_unique.py` | New |
| `backend/app/startup.py` | Modified |
| `backend/app/models_crud/service.py` | Modified |
| `backend/app/models_crud/router.py` | Modified |
| `frontend/src/routes/models/[id]/+page.svelte` | Modified |
| `backend/tests/test_sets/test_crud.py` | Modified |
| `backend/tests/test_models/test_model_hierarchy.py` | Modified |
