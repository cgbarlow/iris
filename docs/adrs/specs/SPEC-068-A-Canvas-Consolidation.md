# SPEC-068-A: Canvas Consolidation

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-068-A |
| **ADR** | [ADR-068](../ADR-068-Canvas-Consolidation.md) |
| **Status** | Draft |
| **Date** | 2026-03-03 |

## Overview

Replace ModelCanvas, FullViewCanvas, and BrowseCanvas with a single UnifiedCanvas component. Replace 30+ individual node/edge components with DynamicNode/DynamicEdge + BaseNode/BaseEdge + notation-specific renderers.

## Architecture

```
UnifiedCanvas.svelte (sets notation context)
  └─> SvelteFlow (nodeTypes=unifiedNodeTypes, edgeTypes=unifiedEdgeTypes)
       ├─> DynamicNode → reads notation from context → dispatches to renderer
       │     ├─> UmlRenderer (class compartments, stereotypes)
       │     ├─> ArchimateRenderer (layer badges)
       │     ├─> SimpleRenderer (icons, basic boxes)
       │     └─> BaseNode (fallback)
       └─> DynamicEdge → reads notation from context → dispatches to renderer
             ├─> UmlEdgeRenderer (UML markers)
             ├─> ArchimateEdgeRenderer (dash patterns)
             ├─> SimpleEdgeRenderer (dash patterns)
             └─> BaseEdge (fallback)
```

## Files

### New
- `BaseNode.svelte` — shared: handles (6), selection, browseMode, labels, a11y
- `BaseEdge.svelte` — shared: routing, EdgeLabel, reconnect anchors, dash array
- `DynamicNode.svelte` — dispatches to renderer based on type + notation
- `DynamicEdge.svelte` — dispatches to edge renderer
- `renderers/SimpleRenderer.svelte` — simple view visuals
- `renderers/UmlRenderer.svelte` — UML compartments, stereotypes
- `renderers/ArchimateRenderer.svelte` — ArchiMate layer styling
- `renderers/SimpleEdgeRenderer.svelte` — simple edge dash patterns
- `renderers/UmlEdgeRenderer.svelte` — UML edge markers
- `renderers/ArchimateEdgeRenderer.svelte` — ArchiMate edge patterns
- `registry.ts` — unified type registries + type equivalences
- `UnifiedCanvas.svelte` — single canvas, notation context, browseMode

### Removed
- ModelCanvas.svelte, FullViewCanvas.svelte, BrowseCanvas.svelte
- All individual node components (10 simple + 11 UML)
- All individual edge components (7 simple + 7 UML)
- Old registry index.ts files

### Kept
- EdgeLabel.svelte — reused by BaseEdge
- NoteLinkEdge.svelte, SelfLoopEdge.svelte — special edge types
- NoteNode.svelte, BoundaryNode.svelte, ModelRefNode.svelte — universal types
