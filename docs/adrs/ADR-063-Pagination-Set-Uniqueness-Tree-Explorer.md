# ADR-063: Pagination Disabled Styling, Set Name Uniqueness Fix, Model Tree Explorer

## Proposal: Visual Disabled State for Pagination, Partial Unique Index for Soft-Deleted Sets, Hierarchy Tree Sidebar on Model Detail

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-063 |
| **Initiative** | Post-v1.7.0 Fixes & Model Hierarchy Navigation |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-02 |
| **Status** | Approved |
| **Dependencies** | ADR-060 (Sets), ADR-058 (SparxEA Integration) |

---

## ADR (WH(Y) Statement format)

**In the context of** Iris v1.7.0 having pagination buttons without visual disabled states, a UNIQUE constraint on the sets table that prevents reusing names of soft-deleted sets, and no tree-based hierarchy navigation on the model detail page,

**facing** user confusion about pagination button state, inability to create a set with the same name as a previously deleted set, and difficulty navigating complex model hierarchies from the detail page,

**we decided for** adding Tailwind `disabled:opacity-50 disabled:cursor-not-allowed` classes to pagination buttons, replacing the full UNIQUE constraint on `sets.name` with a partial unique index scoped to active rows (`WHERE is_deleted = 0`), and adding a collapsible tree sidebar to the model detail page with hierarchy management capabilities (add child, set parent),

**and neglected** JavaScript-based disabled styling (Tailwind already handles this natively), application-level uniqueness checks before INSERT (race conditions, less robust than database constraints), and a modal tree picker (less discoverable, blocks the main content),

**to achieve** clear visual feedback for pagination state, correct soft-delete semantics for set names, and efficient hierarchy navigation and management from the model detail page,

**accepting that** the SQLite migration requires table recreation to drop the original UNIQUE constraint, and the tree sidebar adds visual complexity to the model detail page.

---

## Decisions

1. **Pagination disabled styling**: Use `disabled:opacity-50 disabled:cursor-not-allowed` Tailwind classes on Prev/Next buttons in `Pagination.svelte` and the audit log page's inline pagination
2. **Partial unique index**: New migration m014 recreates the sets table without the UNIQUE constraint on name, then adds `CREATE UNIQUE INDEX idx_sets_name_active ON sets(name) WHERE is_deleted = 0`
3. **Tree sidebar**: Collapsible sidebar on model detail page showing set-scoped hierarchy tree using existing `TreeNode` component
4. **Set-scoped hierarchy API**: Add optional `set_id` query parameter to `GET /api/models/hierarchy`
5. **Hierarchy management**: "Add Child" button in sidebar creates child models; "Parent" field in overview tab with ModelPicker for reparenting
6. **Reuse existing components**: TreeNode, ModelDialog, ModelPicker, and ConfirmDialog are used as-is

---

## Specification

See [SPEC-063-A](specs/SPEC-063-A-Pagination-Set-Uniqueness-Tree-Explorer.md).
