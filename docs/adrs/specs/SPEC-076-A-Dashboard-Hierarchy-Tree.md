# SPEC-076-A: Dashboard Hierarchy Tree

**ADR:** [ADR-076](../ADR-076-Dashboard-Hierarchy-Tree.md)
**Status:** Approved
**Date:** 2026-03-04

---

## Overview

Add the diagram hierarchy tree to the dashboard page, visible only when a set is selected. Reuse the existing `TreeNode` component and the existing `/api/diagrams/hierarchy?set_id=` endpoint. No new components or backend changes are needed.

## Frontend Changes

### File: `frontend/src/routes/+page.svelte`

**New imports:**
- `TreeNode` from `$lib/components/TreeNode.svelte`
- `DiagramHierarchyNode` from `$lib/types/api`

**New state:**
- `hierarchyTree: DiagramHierarchyNode[]` — the tree data from the API
- `hierarchyLoading: boolean` — loading state for the hierarchy fetch
- `treeSearchQuery: string` — search input value for filtering tree nodes
- `treeExpandedIds: Set<string>` — tracks which tree nodes are expanded

**New function: `loadHierarchy()`**
- Called inside `loadDashboard()` when `setId` is truthy
- Fetches `GET /api/diagrams/hierarchy?set_id={setId}`
- Sets `hierarchyTree` on success, empty array on failure

**New template section** (after stats cards, before search section):
- Conditional on `activeSet` being truthy
- Section heading "Diagram Hierarchy"
- Search input (`id="tree-search"`) for filtering tree nodes
- `<ul role="tree">` containing `{#each hierarchyTree as node}` rendering `<TreeNode>`
- Loading spinner when `hierarchyLoading` is true
- Empty state message when tree has no nodes

## TreeNode Props Used

| Prop | Value |
|------|-------|
| `node` | Each `DiagramHierarchyNode` from `hierarchyTree` |
| `searchQuery` | `treeSearchQuery` |
| `expandedIds` | `treeExpandedIds` |

## Acceptance Criteria

1. Dashboard page imports `TreeNode` component
2. Dashboard page imports `DiagramHierarchyNode` type
3. Dashboard calls `/api/diagrams/hierarchy` endpoint when set is selected
4. Hierarchy section renders with `role="tree"` for accessibility
5. Tree search input exists for filtering nodes
6. Hierarchy section is conditional on `activeSet` being truthy
7. `TreeNode` receives `searchQuery` prop
8. `TreeNode` receives `expandedIds` prop
9. Clicking a tree node navigates to `/diagrams/{id}` (built into TreeNode)
10. Loading and empty states are handled
