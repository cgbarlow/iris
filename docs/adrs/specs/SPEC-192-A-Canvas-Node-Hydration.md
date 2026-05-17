# SPEC-192-A: Canvas node hydration from element

Implements: [ADR-192](../ADR-192-Canvas-Node-Hydration-From-Element.md)
Resolves: Issue [#164](https://github.com/cgbarlow/iris/issues/164)
Status: Living

## Surface

Single helper exported from `frontend/src/lib/canvas/elementToNodeData.ts`:

```ts
export interface ElementNodeData {
  label: string;
  entityType: SimpleEntityType;
  description: string;
  entityId: string;
  notation: string;
  attributes?: unknown;
  operations?: unknown;
  literals?: unknown;
  stereotype?: unknown;
  qualifier?: unknown;
  visual?: NodeVisualOverrides;
  diagramUsageCount: number;
  [key: string]: unknown;            // mirror CanvasNodeData
}

export function elementToNodeData(element: Element): ElementNodeData;
```

The open index signature keeps the helper assignable directly to
`CanvasNodeData` without a cast.

## Call sites

| File:line | Function | Behaviour |
|---|---|---|
| `frontend/src/routes/views/[id]/+page.svelte:~1156` | `handleAddElement` (non-BPMN branch) | New node's `data` is `elementToNodeData(created)` from the POST response. |
| `frontend/src/routes/views/[id]/+page.svelte:~1556` | `handleLinkElement` (non-BPMN branch) | Same shape when binding an existing element to a fresh canvas node. |
| `frontend/src/routes/views/[id]/+page.svelte:~614` | `refreshNodeDescriptions` | For each node with `entityId`, fetch the element, hydrate via the helper, merge over existing data (preserves canvas-specific keys), keep the description "starts-with-label" trim for BPMN. |

`refreshNodeDescriptions` diff-checks the hydrated fields
(`label / description / diagramUsageCount / attributes / operations /
literals / stereotype / qualifier`) and only triggers a state update
when at least one has changed.

## Fields hydrated and their sources

| Field on node.data | Source on Element | Default |
|---|---|---|
| `label` | `element.name` | (required) |
| `entityType` | `element.element_type` cast to `SimpleEntityType` | (required) |
| `description` | `element.description` | `''` |
| `entityId` | `element.id` | (required) |
| `notation` | `element.notation` | `'simple'` |
| `attributes` | `element.data.attributes` | `undefined` |
| `operations` | `element.data.operations` | `undefined` |
| `literals` | `element.data.literals` | `undefined` |
| `stereotype` | `element.data.stereotype` | `undefined` |
| `qualifier` | `element.data.qualifier` | `undefined` |
| `visual` | `element.data.visual` | `undefined` |
| `diagramUsageCount` | `element.diagram_usage_count` | `0` |

BPMN-specific shape (`bpmnDefaultDiscriminators`) is **not** routed
through this helper — BPMN nodes have a different `data` contract
(see `handleAddElement` BPMN branch). Future refactor could collapse
the BPMN branch too, but is out of scope for issue #164.

## Tests

`frontend/tests/unit/elementToNodeData.test.ts` — 9 cases:

1. Carries label, entityType, entityId, description, notation.
2. Coerces missing description to empty string.
3. Defaults notation to "simple".
4. Hydrates class attributes from `data.attributes`.
5. Hydrates operations + literals + stereotype + qualifier.
6. Passes through `visual` overrides.
7. Handles an element with no `data` field.
8. Reads `diagramUsageCount` from `diagram_usage_count`.
9. Defaults `diagramUsageCount` to 0.

## Acceptance criteria

- Class elements show their attributes on every diagram they appear
  on, including after attributes are added/edited via
  `/elements/[id]` (without a hard reload — `refreshNodeDescriptions`
  picks them up on next navigation back to the diagram).
- No regression to BPMN flow, which still uses
  `bpmnDefaultDiscriminators` for `data.data`.
- No regression to undo/redo — node `data` remains canvas-state of
  record; the helper just keeps it complete and refreshed.

## Verification

```
cd frontend
npx vitest run tests/unit/elementToNodeData.test.ts \
                tests/unit/markdownView.test.ts \
                tests/unit/packageRelationshipsTab.test.ts \
                tests/unit/elementTemplates.test.ts \
                tests/unit/hierarchyControls.test.ts \
                tests/unit/packagesPageHierarchy.test.ts
```

All green.

Manual:

1. `./scripts/dev.sh restart`
2. Browse to a class element. Add 2 attributes; save.
3. Open a diagram that contains the element. Attributes show in the
   class compartment.
4. Add the same element to a new diagram via "Link Element" — the
   new node also renders with the attributes.
