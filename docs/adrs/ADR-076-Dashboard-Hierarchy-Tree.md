# ADR-076: Dashboard Hierarchy Tree

## Proposal: Display diagram hierarchy tree on dashboard when a set is selected

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-076 |
| **Initiative** | Dashboard Enhancement |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-04 |
| **Status** | Approved |
| **Dependencies** | ADR-071 |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris dashboard showing only count cards and bookmarks when a set is selected,

**facing** users who want to browse the diagram structure without navigating away from the dashboard,

**we decided for** adding the existing `TreeNode` hierarchy tree component to the dashboard page, visible only when a set is selected, fetching data from the existing `/api/diagrams/hierarchy?set_id=` endpoint,

**and neglected** building a new tree component or a simplified list view (the existing TreeNode already provides search, expand/collapse, keyboard navigation, and content indicators),

**to achieve** quick browsing and navigation of the diagram hierarchy directly from the dashboard, with zero new components (Protocol 13 — DRY),

**accepting that** the hierarchy section is only visible when a set is selected, and clicking a tree node navigates to the diagram detail page.

---

## Decisions

1. **Reuse TreeNode component**: The existing `TreeNode.svelte` recursive component provides all needed functionality — expand/collapse, search filtering, keyboard navigation, and content indicators
2. **Reuse hierarchy API**: The existing `GET /api/diagrams/hierarchy?set_id=` endpoint returns the tree data
3. **Conditional rendering**: The hierarchy section only appears when `activeSet` is truthy (a set is selected via `set_id` query parameter)
4. **Tree search**: A dedicated search input filters tree nodes by name using the `searchQuery` prop
5. **Placement**: The hierarchy section appears after the stats cards and before the global search section

---

## Specification

See [SPEC-076-A](specs/SPEC-076-A-Dashboard-Hierarchy-Tree.md).
