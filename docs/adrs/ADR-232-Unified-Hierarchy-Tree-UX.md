# ADR-232: Unified hierarchy-tree UX (diagram nesting, element icon, collapse, consistent controls)

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-232 |
| **Initiative** | Make the navigation hierarchy coherent now that element containment (ADR-231) adds element nodes |
| **Proposed By** | Engineering |
| **Date** | 2026-06-01 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the navigation hierarchy after element containment
(ADR-231) landed — the tree now shows packages, diagrams **and** nested
elements — surfaced by importing the GEANZ set,

**facing** five defects: (1) imported diagrams render in a separate block
*below* the element-containment tree instead of nested where they belong —
GEANZ capability diagrams are EA composite diagrams whose owning element
carries `detail_diagram_id`, but the hierarchy attaches them by
`parent_package_id`, and the `manual` sort leads with `node_type` so
diagrams/elements/packages group into type-blocks; (3) the element detail
screen has no hierarchy sidebar (dashboard/view/package do); (4) the
"Reorder" affordance exists only on the dashboard; (5) packages and element
containments are expanded by default, drowning the user in nodes; (6) there
is no visual way to tell node *types* apart now that elements appear,

**we decided to**:
  - **(1)** In `get_diagram_hierarchy` nest a diagram under its owning
    element when one exists: `LEFT JOIN elements e ON e.detail_diagram_id =
    d.id` and use `COALESCE(e.id, d.parent_package_id)` as the parent key;
    and change the `manual` sort to interleave siblings by
    `sequence_order, name` (drop the leading `node_type`) so diagrams,
    elements and sub-packages sit in document order. Read-time only — no
    re-import.
  - **(6)** Render the existing **cube** icon (via `IconDisplay`) on
    `node_type:'element'` tree nodes; leave the diagram blue solid/hollow
    content indicator and the package node exactly as they are.
  - **(5)** Default the tree to **collapsed** (only the root level shown),
    auto-revealing just the ancestor chain of the current node; search/peek
    expansion is unchanged.
  - **(3)+(4)+DRY** Extract a single `HierarchySidebar.svelte` (the sidebar
    is duplicated ~6× across dashboard, views, package and the view-detail
    page) owning the drawer, search, `HierarchyControls`, the Reorder
    toggle, and the `TreeNode` loop; mount it on **all four** surfaces
    including the element screen, so Show + Reorder + collapse behave
    identically everywhere. Element-containment nodes stay non-draggable in
    v1 (reorder persists diagrams/packages only).

**because** element nodes made the tree ambiguous and inconsistent across
screens; nesting diagrams under their owning element matches the EA model
the user expects; and consolidating the duplicated sidebar (Protocol §13)
is the only sane way to make controls/behaviour consistent without 6× edits.

## Consequences
- The GEANZ tree reads like the EA Project Browser: zone → capability →
  sub-capability, with each capability's diagram nested under it.
- One `HierarchySidebar` is the single source of truth for tree UX; future
  changes touch one file.
- Collapsed-by-default scales to large sets; the active item is still
  revealed.
- Risk: the sidebar extraction is a broad refactor — mitigated by being
  behaviour-preserving and covered by existing page e2e, done as a discrete
  first step.

## Alternatives considered
- Leave diagrams under packages, add a separate "diagrams" section — rejected
  (that's the very split the user flagged as wrong).
- Per-screen sidebar tweaks without extraction — rejected (6× duplication,
  drift).
- A new `parent_element_id` field on the hierarchy node — unnecessary; the
  generic `parent_package_id` key already carries any parent id.

## Surface parity (§14) / SQLite↔Supabase (§15)
No schema change and no new write endpoint. `PUT /api/diagrams/reorder` is
already verb-`None` to the parity checker; exposing Reorder on more frontends
adds no backend write. Parity stays green; no migration.

## Dependencies
Builds on ADR-231 (element nodes) and ADR-158 (`package_hierarchy`).
Spec: `docs/adrs/specs/SPEC-232-A-Unified-Hierarchy-Tree-UX.md`.
