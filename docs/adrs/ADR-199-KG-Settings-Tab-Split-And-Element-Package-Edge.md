# ADR-199: KG settings split + first-class element ↔ package edges

Status: Accepted (2026-05-18)
Bundles: issue [#173](https://github.com/cgbarlow/iris/issues/173) items 4 and 5.

## Context

Two pieces of UAT feedback that hit the same component and the
same user mental model, so they ship as one release:

**Item 4.** The KG Visibility tab mixed node-type toggles and
relationship-type toggles in a single column. With twelve toggles
in one panel, finding the one you want — particularly toggling a
single relationship without touching node visibility — was
fiddly.

**Item 5.** Elements can belong to packages
(`element.package_id` per `m064_element_package_membership`,
ADR-184), but the graph service did not emit edges for that
relationship. The KG showed elements floating, with no visual
link to the package they belong to, even though packages and
elements were both rendered as nodes in the same view.

The two are coupled in practice: item 5 adds a new toggle to the
relationship-types list, and the natural place for it is the new
"Relationships" tab from item 4. Shipping them in two separate
PRs would either land the new toggle in the old combined tab
(worse UX) or block item 5 on item 4.

## Decision

One PR. Two coordinated changes:

### Tab split (item 4)

`KnowledgeGraphSettings.svelte` widens its `activeTab` union from
`'visibility' | 'display'` to `'nodes' | 'relationships' |
'display'`. The body of the former Visibility tab is split: node
toggles live under "Nodes", edge toggles live under
"Relationships". Display tab is unchanged.

Default tab on first open: `'nodes'` (preserves the
"node-type-first" mental model of the previous Visibility tab —
that section's heading was at the top).

The `onResetToDefaults` prop signature widens to the new union.
The dashboard's caller switches to per-tab reset semantics: each
tab resets only its own concern (nodes resets `nodes`,
relationships resets `edges`, display resets physics). This was
already the user's intent — the old code reset both nodes and
edges from the single "Visibility" tab because there was nowhere
finer-grained to reset from. Now there is.

### Element ↔ package edge (item 5)

`get_graph_data` selects `e.package_id` alongside the existing
element columns, and emits one `package → element` edge per
element whose `package_id` resolves to a package in the scoped
set. Edge direction matches the existing `set_membership` and
`hierarchy` conventions: containers point at their contents.

`element_package` is added to `GraphDisplaySettings.edges` and to
`GRAPH_SETTINGS_DEFAULTS` with default `True`. The frontend
exposes the toggle in `EDGE_GROUPS` under the **Package** group
(alongside `hierarchy` and `package_relationship`).

## Why this edge direction (package → element)

Consistency. Every other "containment" edge in the graph points
container → contents:

| Edge | Direction |
|---|---|
| `collection_membership` | collection → set |
| `set_membership` | set → element / diagram / package |
| `hierarchy` | parent_package → child_package / diagram |
| `diagram_element` | diagram → element |
| `element_package` (this PR) | **package → element** |

Reversing for elements alone would be a needless inconsistency.

## Why default ON

Symmetric with the other containment edges. Users who don't want
to see package membership can turn it off; users who never opened
the settings dialog should see the most informative view by
default.

## Why no per-element-type granularity

Out of scope. The toggle is one boolean for "show element-to-
package edges at all". Per-type filtering (only show
`component → package` but not `interface → package`, say) is a
separate feature with no current user demand.

## Consequences

- `backend/app/graph/models.py:36-51` — `element_package: True` in
  `GraphDisplaySettings.edges` default.
- `backend/app/graph/service.py:211,367-397,444-451` — element
  SELECT adds `package_id`, new edge-generation block emits
  `element_package` edges, `GRAPH_SETTINGS_DEFAULTS` includes the
  key.
- `backend/tests/test_graph/test_element_package_edges.py` — new
  pytest module, 4 cases (defaults, emit-with-package,
  no-emit-without-package, node typing sanity).
- `frontend/src/lib/components/KnowledgeGraphSettings.svelte` —
  `activeTab` union widened, three tab buttons, two `{#if}`
  branches for the split, `element_package` toggle added to the
  Package group in `EDGE_GROUPS`.
- `frontend/src/lib/components/KnowledgeGraph.svelte:17` — prop
  signature widened to match.
- `frontend/src/routes/+page.svelte:690-702` — `onResetToDefaults`
  caller switches to per-tab reset semantics.
- `frontend/tests/unit/kgSettingsTabSplit.test.ts` — new static-
  parser test (12 assertions) covers tab structure, body gating,
  edge toggle placement, prop signature.
- CHANGELOG `[6.9.0]`. Minor bump — new feature surface.

## Verification

```
.venv/bin/python -m pytest backend/tests/test_graph/
cd frontend && npx vitest run tests/unit/kgSettingsTabSplit.test.ts
```

Both green. Manual smoke: open KG with a set that has elements
assigned to packages; confirm package→element edges render; open
settings, confirm three tabs (Nodes / Relationships / Display);
toggle the new "Elements (membership)" item under the Package
group and confirm the edges hide.

## See also

- Issue [#173](https://github.com/cgbarlow/iris/issues/173) items 4, 5.
- [ADR-184](ADR-184-Element-Package-Membership.md) — the
  `element.package_id` column this edge surfaces.
- [ADR-189](ADR-189-Package-Relationships-Tab.md) — the table
  view of the same relationship on the package detail page.
