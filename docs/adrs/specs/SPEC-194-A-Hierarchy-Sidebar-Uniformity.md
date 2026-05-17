# SPEC-194-A: Hierarchy sidebar uniformity

Implements: [ADR-194](../ADR-194-Hierarchy-Sidebar-Uniformity.md)
Resolves: Issue [#162](https://github.com/cgbarlow/iris/issues/162)
Status: Living

## Shared component

`frontend/src/lib/components/HierarchyControls.svelte`

```svelte
interface Props {
  showDiagrams: boolean;
  showText: boolean;
  onShowDiagrams: (v: boolean) => void;
  onShowText:     (v: boolean) => void;
  oncreateview:    () => void;
  oncreatepackage: () => void;
}
```

Density: trigger buttons `px-2 py-1 text-xs`; dropdown menu items
`px-3 py-1 text-xs`; Show checkboxes `px-3 py-1 text-xs`. No `size`
prop — single density.

## Call sites

| File:line | Wires |
|---|---|
| `frontend/src/routes/+page.svelte:631` | Dashboard root — creates top-level packages and views |
| `frontend/src/routes/views/+page.svelte:390` | Views list — creates top-level packages and views |
| `frontend/src/routes/views/[id]/+page.svelte:2088` | View detail sidebar — creates *child* of current diagram's package |
| `frontend/src/routes/packages/[id]/+page.svelte:~514` | Packages detail sidebar — creates *child* of current package |

All four pass `{showDiagrams}` / `{showText}` (Svelte 5 shorthand).
On the two detail pages, the `oncreatepackage` / `oncreateview`
handlers open the page-specific child-creation dialogs.

## TreeNode prop normalisation

`TreeNode` accepts both `showDiagrams` / `showText` (issue #27 era)
and the older `showDiagramsOnly` boolean. The packages-detail page
historically used `showDiagramsOnly`; this spec drops that path so
all surfaces drive `TreeNode` the same way. `showDiagramsOnly`
remains in `TreeNode`'s prop list because no caller uses it after
this change — a future cleanup can delete the dead branch.

## Tests

`frontend/tests/unit/hierarchyControls.test.ts` — adds 3 cases:

1. Trigger buttons use compact `px-2 py-1 text-xs`.
2. Dropdown items use compact `px-3 py-1 text-xs`.
3. The old larger `px-3 py-1.5 text-sm` / `px-4 py-1.5 text-sm`
   strings are gone.

`frontend/tests/unit/packagesPageHierarchy.test.ts` (new) — 5 cases:

1. `HierarchyControls` is imported.
2. It's mounted in the sidebar.
3. `oncreatepackage` and `oncreateview` wire to the existing
   child-creation dialog flags.
4. The old bespoke `showChildMenu` / `+ Child` dropdown is gone.
5. `TreeNode` receives `showDiagrams` / `showText`, not
   `showDiagramsOnly`.

## Acceptance criteria

- Visual density across Dashboard / Views / View detail / Packages
  detail is identical.
- "+ New" dropdown on every surface offers the same Package / View
  pair (sub-meanings differ — root vs child).
- Show checkboxes (`Diagrams`, `Text`) drive `TreeNode` filtering
  identically on every surface.
- No regression to the existing keyboard/aria affordances on
  `HierarchyControls`.

## Verification

```
npx vitest run \
  tests/unit/hierarchyControls.test.ts \
  tests/unit/packagesPageHierarchy.test.ts \
  tests/unit/hierarchyControlsViews.test.ts \
  tests/unit/dashboardHierarchy.test.ts \
  tests/unit/packageRelationshipsTab.test.ts
```

All green.

Manual smoke per ADR-194.
