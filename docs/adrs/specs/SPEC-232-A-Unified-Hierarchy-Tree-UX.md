# SPEC-232-A: Unified hierarchy-tree UX

Implements **[ADR-232](../ADR-232-Unified-Hierarchy-Tree-UX.md)**.

## Backend (issue 1)
`backend/app/diagrams/service.py` `get_diagram_hierarchy`:
- Diagram UNION arm: `LEFT JOIN elements e ON e.detail_diagram_id = d.id AND e.is_deleted = 0`, emit `COALESCE(e.id, d.parent_package_id) AS parent_package_id`.
- `_HIERARCHY_ORDER_BY['manual']`: `t.sequence_order, t.name` (interleave; elements emit `sequence_order` via `COALESCE(..., 0)` so they don't all sort first — use a name tiebreak).

## Frontend
- **(6) cube icon** — `TreeNode.svelte`: when `isElement`, render the existing icon-system cube via `IconDisplay`; diagram indicator (`:221-225`) and package unchanged.
- **(5) collapse** — `TreeNode.svelte`: default `autoExpandDepth=0`; stop the dashboard `calcAutoExpandDepth` auto-fit; `HierarchySidebar` seeds `expandedIds` with the current node's ancestor chain.
- **(STEP 0) `HierarchySidebar.svelte`** (NEW) — owns `<aside data-hierarchy-sidebar>` + ADR-229 drawer, search, `HierarchyControls`, `reorderMode` + `handleReorder` (→ `PUT /api/diagrams/reorder`), the `TreeNode` loop, `loadHierarchyTree()`, the `iris-hierarchy-sidebar-open` localStorage toggle. Props: `setId`, `currentId`, create-handlers, optional AI-context (dashboard), `onreorder`.
- **(3) element screen** — mount `HierarchySidebar` on `routes/elements/[id]/+page.svelte` seeded from `entity.set_id`, `currentId={entity.id}`.
- **(4) reorder everywhere** — `HierarchySidebar` carries the Reorder toggle on dashboard/view/package/element; element-containment nodes stay non-draggable.
- Re-point dashboard / `views/+page` / `packages/[id]` / `views/[id]` to the shared component (behaviour-preserving).

## Acceptance
- AC1 a composite diagram (`detail_diagram_id` set) nests under its owning element, not its package; siblings interleave by position.
- AC2 element tree nodes show the cube; diagram/package indicators unchanged.
- AC3 tree loads collapsed (root only); current node's ancestors revealed; search expands matches.
- AC4 element screen has the sidebar; Show + Reorder work on all four screens.
- AC5 non-GEANZ sets' hierarchy unchanged (regression test).
