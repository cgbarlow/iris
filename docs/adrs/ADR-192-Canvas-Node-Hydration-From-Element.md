# ADR-192: Canvas node hydration from element

Status: Accepted (2026-05-17)
Extends: [ADR-184](ADR-184-Element-Package-Membership.md), [ADR-190](ADR-190-Class-Diagram-Type-Under-Simple-Notation.md)
Implements: Issue [#164](https://github.com/cgbarlow/iris/issues/164)
Spec: [SPEC-192-A](specs/SPEC-192-A-Canvas-Node-Hydration.md)

## Context

Issue [#164](https://github.com/cgbarlow/iris/issues/164) — two
class-UML elements ("rankedtrajectory" and "test ingredient") rendered
inconsistently on the canvas. Same `notation=uml`, same
`element_type=class`, same theme, but one showed its attribute
compartment populated while the other showed only the name with no
visible attributes.

Investigation traced the divergence to **how each element's canvas
node was minted**, not to the renderer:

- `frontend/src/lib/canvas/renderers/UmlRenderer.svelte` reads
  `data.attributes` off the node and renders the compartment under
  `{#if attributes && attributes.length > 0}`. The renderer is
  innocent — given the right data, it renders correctly.
- The view-detail page (`frontend/src/routes/views/[id]/+page.svelte`)
  had **three** places that built `node.data` from an `Element`:
  1. `handleAddElement` (create new element on canvas) — populated
     only `label / entityType / description / entityId / notation`.
  2. `handleLinkElement` (link an existing element onto canvas) —
     same shape; dropped any class attributes the source element had.
  3. `refreshNodeDescriptions` (post-load sync from the backend) —
     synced `label / description / diagramUsageCount` only.

So if a user authored class attributes on `/elements/[id]` after the
node was placed, the canvas node never picked them up. Two class
elements created on different paths would render with totally
different completeness.

This is also a Protocol §13 (DRY) violation: three near-identical
mini-builders that drifted apart in subtle ways.

## Decision

Introduce a single source of truth for "given a backend `Element`,
produce the canvas node `data` payload":

```ts
// frontend/src/lib/canvas/elementToNodeData.ts
export function elementToNodeData(element: Element): ElementNodeData {
  const data = (element.data ?? {}) as Record<string, unknown>;
  return {
    label: element.name,
    entityType: element.element_type as SimpleEntityType,
    description: element.description ?? '',
    entityId: element.id,
    notation: element.notation ?? 'simple',
    attributes:  data.attributes,
    operations:  data.operations,
    literals:    data.literals,
    stereotype:  data.stereotype,
    qualifier:   data.qualifier,
    visual:      data.visual as NodeVisualOverrides | undefined,
    diagramUsageCount: element.diagram_usage_count ?? 0,
  };
}
```

All three call sites on `views/[id]/+page.svelte` are refactored to
use this helper. `refreshNodeDescriptions` keeps its description
"starts-with-label" trim for BPMN-style payloads, but otherwise
performs a wholesale merge of the hydrated fields.

`ElementNodeData` declares an open index signature `[key: string]:
unknown` so it remains assignable to `CanvasNodeData`.

## Why not bake this into the renderer

The renderer's contract is to read from `node.data`. Making it fetch
the element on the fly would mean a network call per render — bad
for canvases with dozens of nodes — and would break the
dirty-tracking model that powers undo/redo. The canvas-stored copy
of `data` remains the source of truth for the canvas; the helper
just ensures the copy is *complete* the moment it's minted and
*refreshed* whenever `refreshNodeDescriptions` runs.

## Why not store attributes on the canvas

The element's `data` payload already lives in `element_versions.data`
on the backend. Duplicating it in the diagram's `nodes[].data` would
diverge two sources of truth (which is what caused #164 in the first
place). The helper closes the loop: every time the canvas reads, it
hydrates from the element; every time the user navigates back, it
re-hydrates.

## Consequences

- New file: `frontend/src/lib/canvas/elementToNodeData.ts`.
- Refactor: three call sites on
  `frontend/src/routes/views/[id]/+page.svelte` use the helper.
- Tests: `frontend/tests/unit/elementToNodeData.test.ts` — 9 shape
  cases covering class attributes, operations, literals, visual
  overrides, missing data, default diagramUsageCount.
- No backend changes; no migration; no MCP / CLI changes.
- CHANGELOG `[6.8.1]` Fixed entry referencing #164.

## Verification

- `npx vitest run tests/unit/elementToNodeData.test.ts` — 9 green.
- `npx vitest run tests/unit/markdownView.test.ts tests/unit/packageRelationshipsTab.test.ts tests/unit/elementTemplates.test.ts tests/unit/hierarchyControls.test.ts` — full suite remains green.
- Manual smoke on `./scripts/dev.sh start`: edit a class element's
  attributes on `/elements/[id]`, return to a diagram containing
  that element, attributes appear in the compartment after
  `refreshNodeDescriptions` fires.

## See also

- Issue [#164](https://github.com/cgbarlow/iris/issues/164).
- [ADR-190](ADR-190-Class-Diagram-Type-Under-Simple-Notation.md) —
  the prior class-under-simple work that surfaced this gap.
- `frontend/src/lib/canvas/renderers/UmlRenderer.svelte:75` — the
  consumer of the hydrated shape.
