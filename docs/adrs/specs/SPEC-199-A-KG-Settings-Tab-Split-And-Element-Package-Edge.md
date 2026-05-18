# SPEC-199-A: KG settings tab split + element-package edges

Implements: [ADR-199](../ADR-199-KG-Settings-Tab-Split-And-Element-Package-Edge.md)
Resolves: Issue [#173](https://github.com/cgbarlow/iris/issues/173) items 4, 5
Status: Living

## Frontend tab structure

`frontend/src/lib/components/KnowledgeGraphSettings.svelte`:

```ts
let activeTab = $state<'nodes' | 'relationships' | 'display'>('nodes');
```

Three tab buttons in order: **Nodes** | **Relationships** |
**Display**. Each branch renders only its own controls:

| Tab | Renders |
|---|---|
| Nodes | `{#each Object.entries(NODE_TYPE_LABELS)}` node checkboxes with colour swatches |
| Relationships | `{#each EDGE_GROUPS}` group → items, with tri-state group toggle |
| Display | Label density, spread, size contrast sliders |

## EDGE_GROUPS structure (Relationships tab)

```ts
const EDGE_GROUPS = [
  { label: 'Containment', items: [
    { key: 'collection_membership', label: 'Collection → Sets' },
    { key: 'set_membership',         label: 'Set → Contents' },
    { key: 'direct_diagram_links',   label: 'Direct diagram links' },
  ]},
  { label: 'Package', items: [
    { key: 'hierarchy',            label: 'Nesting' },
    { key: 'package_relationship', label: 'Relationships' },
    { key: 'element_package',      label: 'Elements (membership)' },  // ← new
  ]},
  { label: 'Diagram', items: [
    { key: 'diagram_element', label: 'Elements' },
    { key: 'diagram_package', label: 'References' },
    { key: 'diagram_link',    label: 'Navigation' },
  ]},
  { label: 'Element', items: [
    { key: 'element_relationship', label: 'Relationships' },
  ]},
];
```

## Backend graph emission

`backend/app/graph/service.py`:

- Element SELECT now grabs `e.package_id` as `row[5]`.
- New edge-generation block (section 8b):

```python
for row in element_rows:
    eid, pkg_id = row[0], row[5]
    if pkg_id and pkg_id in package_ids:
        edges.append({
            "id": str(uuid.uuid4()),
            "source": pkg_id, "target": eid,
            "relationship_type": "contains",
            "label": None,
            "edge_type": "element_package",
        })
```

Edge direction: **package → element** (container → contents, matching
`set_membership` and `hierarchy`).

## Defaults

Both `GraphDisplaySettings.edges` (pydantic model) and
`GRAPH_SETTINGS_DEFAULTS` (service-layer settings store) include:

```python
"element_package": True
```

## Per-tab reset semantics

`frontend/src/routes/+page.svelte` `onResetToDefaults` handler:

```ts
if (tab === 'nodes') {
  graphSettings = { ...graphSettings, nodes: { ...defaults.nodes } };
} else if (tab === 'relationships') {
  graphSettings = { ...graphSettings, edges: { ...defaults.edges } };
} else {
  graphSettings = { ...graphSettings, label_density: ..., node_spacing: ..., size_contrast: ..., link_length: ... };
}
```

## Acceptance criteria

1. Opening KG settings shows three tab buttons; Nodes is active
   by default.
2. Switching to Relationships shows only edge toggles (with group
   tri-state); switching to Nodes shows only node toggles.
3. Resetting from the Relationships tab restores edge defaults
   without disturbing node toggles, and vice versa.
4. Opening KG for a set with elements assigned to packages shows
   `package → element` edges by default.
5. Toggling "Elements (membership)" off in the Package group
   hides those edges.
6. No other edge type's visibility, default, or rendering changes.

## Tests

Backend — `backend/tests/test_graph/test_element_package_edges.py`:

1. `element_package` appears in `GraphDisplaySettings.edges`
   defaults with value `True`.
2. `GET /api/graph?set_id=...` emits one `element_package` edge
   per element with a `package_id` resolving to a package in
   scope (correct source/target).
3. Element with no `package_id` produces no edge.
4. Edge addition doesn't change node typing.

Frontend — `frontend/tests/unit/kgSettingsTabSplit.test.ts`:

1-6. Tab structure: union is widened; default is `'nodes'`; three
   tab buttons present; old `'visibility'` key gone.
7. Nodes branch gated on `activeTab === 'nodes'`.
8-9. Relationships branch gated on `activeTab === 'relationships'`;
   `EDGE_GROUPS` still iterated.
10-11. `element_package` toggle key exists and sits under the
   Package group.
12. `onResetToDefaults` prop widened to the new union.

## Verification

```
.venv/bin/python -m pytest backend/tests/test_graph/
cd frontend && npx vitest run tests/unit/kgSettingsTabSplit.test.ts
```

Both green. Manual smoke per ADR-199 verification section.
