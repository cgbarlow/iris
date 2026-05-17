# ADR-194: Hierarchy sidebar uniformity across Dashboard / Views / Packages

Status: Accepted (2026-05-17)
Extends: [ADR-189](ADR-189-Package-Relationships-Tab.md)
Implements: Issue [#162](https://github.com/cgbarlow/iris/issues/162)
Spec: [SPEC-194-A](specs/SPEC-194-A-Hierarchy-Sidebar-Uniformity.md)

## Context

Issue [#162](https://github.com/cgbarlow/iris/issues/162) — the
hierarchy panel on the views page had buttons that were too large
after the v5.6.1 DRY refactor (which unified Dashboard and Views to
the shared `HierarchyControls.svelte`). The packages-detail page,
on the other hand, had a bespoke inline dropdown ("+ Child" → Diagram
/ Package) and a "Diagrams" toggle button that the user liked
visually but did **not** use the shared component.

So the actual state in v6.8.0 was:

| Surface | Hierarchy controls source |
|---|---|
| Dashboard (`/+page.svelte`) | `<HierarchyControls>` (large buttons) |
| Views list (`/views/+page.svelte`) | `<HierarchyControls>` (large buttons) |
| View detail (`/views/[id]/+page.svelte`) | `<HierarchyControls>` (large buttons) |
| Package detail (`/packages/[id]/+page.svelte`) | **Bespoke inline dropdown + Diagrams toggle** (compact buttons) |

Two failure modes:
1. **Visual inconsistency** — the shared component's `px-3 py-1.5
   text-sm` buttons read large compared to the surrounding UI on the
   detail pages, while the bespoke packages compact controls felt
   right.
2. **DRY drift** — packages detail re-implemented the "+ New →
   Package | Diagram" dropdown UI logic the shared component already
   owned. The packages page also passed `showDiagramsOnly` to
   `TreeNode` while the other surfaces passed `showDiagrams` /
   `showText`.

The user's brief: "use the same code from dashboard for hierarchy
area on view page, but styling that the size of the buttons and
text uses is as per the 'packages' screen, which is as it used to
be on the view screen, and is perfect. Then make 'packages' screen
consistent with the 'view' page."

## Decision

Two changes, paired:

1. **Shrink `HierarchyControls` defaults to compact** —
   `px-2 py-1 text-xs` on the two trigger buttons; `px-3 py-1
   text-xs` on the dropdown menu items and Show checkboxes. No
   `size` prop — every existing caller wants the smaller density;
   YAGNI on the larger variant.
2. **Replace the packages-detail bespoke dropdown with
   `<HierarchyControls>`** — the same component, the same compact
   styling, the same prop shape. The component's `oncreatepackage`
   handler maps to the packages page's `showCreateChildPackageDialog`
   flag; `oncreateview` maps to `showCreateChildDiagramDialog`. The
   packages page drops its `showChildMenu` local state entirely.
3. **Normalise TreeNode props on the packages page** — replace the
   `treeDiagramsOnly` boolean and `showDiagramsOnly` prop with
   `showDiagrams` / `showText` driven by the shared component's
   checkboxes. `TreeNode` already accepts both shapes (it has
   carried `showDiagrams` / `showText` since #27), so this is a
   prop-rename, not a TreeNode change.

After this change, all four surfaces use the same component and the
same prop names. Future hierarchy work should never reintroduce a
parallel implementation.

## Why not add a size prop

Every existing caller wants the smaller density (the user
explicitly cited packages-page styling as "perfect"). Adding a
size prop would create configuration surface without a real
consumer. If a future surface needs larger buttons it can be added
then, behind a real requirement.

## Why drop `showDiagramsOnly`

The boolean was packages-page-specific and meant "hide packages
that have no descendant diagrams." Its behaviour was strictly a
subset of the more flexible `showDiagrams` / `showText` model: with
both flags on (the default), packages are always shown, and only
text-class diagrams can be hidden. The original use case was
"declutter when looking for diagrams," which is satisfied by
`showText=false`.

## Consequences

- `frontend/src/lib/components/HierarchyControls.svelte` — class
  strings shrunk; no API change.
- `frontend/src/routes/packages/[id]/+page.svelte` — imports
  `HierarchyControls`; drops `showChildMenu` state, drops
  `treeDiagramsOnly` state, adds `showDiagrams` / `showText` state;
  the sidebar header renders `<HierarchyControls>` instead of the
  inline dropdown; `<TreeNode>` invocation uses the new props.
- Existing tests pass without change: Dashboard, Views list and
  View detail already used the shared component — only the visual
  density changes.
- New tests:
  - `frontend/tests/unit/hierarchyControls.test.ts` — three
    assertions for compact class strings.
  - `frontend/tests/unit/packagesPageHierarchy.test.ts` — five
    assertions for the packages-page DRY refactor.
- No backend changes; no migration; no MCP / CLI changes.
- CHANGELOG `[6.8.1]`.

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

Manual:

1. `./scripts/dev.sh start`
2. Visit `/` (Dashboard), `/views`, `/views/{id}`, and
   `/packages/{id}`.
3. The "+ New" / "Show" controls in each hierarchy area read
   visually identical and use the compact density.
4. On `/packages/{id}`, click "+ New" — the dropdown lists
   `Package` and `View` (creating children under the current
   package via the existing dialogs).
5. The Show checkboxes (`Diagrams`, `Text`) drive `TreeNode`'s
   filtering identically across surfaces.

## See also

- Issue [#162](https://github.com/cgbarlow/iris/issues/162).
- [ADR-189](ADR-189-Package-Relationships-Tab.md) — the prior
  packages-detail work that left the hierarchy refactor unfinished.
