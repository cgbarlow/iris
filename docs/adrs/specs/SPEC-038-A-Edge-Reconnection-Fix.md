# SPEC-038-A: Edge Reconnection Fix

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-038-A |
| **ADR Reference** | [ADR-038: Edge Reconnection Fix](../ADR-038-Edge-Reconnection-Fix.md) |
| **Date** | 2026-03-01 |
| **Status** | Active |

---

## Overview

This specification details the changes required to enable edge reconnection in the Iris canvas. The root cause is that @xyflow/svelte v1.5.x requires custom edge components to explicitly render `EdgeReconnectAnchor` elements for endpoint dragging. Without these anchors, the `onreconnect` handler on `<SvelteFlow>` is never triggered because there are no draggable endpoints.

---

## A. EdgeReconnectAnchor Integration

### Import

Each custom edge component must import `EdgeReconnectAnchor` from `@xyflow/svelte`:

```typescript
import { BaseEdge, EdgeReconnectAnchor, getBezierPath, type EdgeProps } from '@xyflow/svelte';
```

### EdgeProps Requirements

`EdgeReconnectAnchor` requires positioning at the source and target endpoints. The `sourceX`, `sourceY`, `targetX`, `targetY` coordinates from `EdgeProps` provide these positions.

### Template Addition

After the existing `BaseEdge` and label markup, add two anchors:

```svelte
<EdgeReconnectAnchor type="source" position={{ x: sourceX, y: sourceY }} />
<EdgeReconnectAnchor type="target" position={{ x: targetX, y: targetY }} />
```

---

## B. Affected Edge Components

### Simple View (5 components)

| File | Edge Type |
|------|-----------|
| `src/lib/canvas/edges/UsesEdge.svelte` | uses |
| `src/lib/canvas/edges/DependsOnEdge.svelte` | depends_on |
| `src/lib/canvas/edges/ComposesEdge.svelte` | composes |
| `src/lib/canvas/edges/ImplementsEdge.svelte` | implements |
| `src/lib/canvas/edges/ContainsEdge.svelte` | contains |

### UML Full View (6 components)

| File | Edge Type |
|------|-----------|
| `src/lib/canvas/uml/edges/AssociationEdge.svelte` | association |
| `src/lib/canvas/uml/edges/AggregationEdge.svelte` | aggregation |
| `src/lib/canvas/uml/edges/CompositionEdge.svelte` | composition |
| `src/lib/canvas/uml/edges/DependencyEdge.svelte` | dependency |
| `src/lib/canvas/uml/edges/RealizationEdge.svelte` | realization |
| `src/lib/canvas/uml/edges/GeneralizationEdge.svelte` | generalization |

### ArchiMate Full View (1 component)

| File | Edge Type |
|------|-----------|
| `src/lib/canvas/archimate/edges/ArchimateEdge.svelte` | All ArchiMate types |

---

## C. Undo History for Reconnection

### ModelCanvas.svelte and FullViewCanvas.svelte

The `handleReconnect` function must push the current state to undo history before applying the edge mutation. The canvas components do not own the history directly — they expose an `onreconnectedge` callback that the parent page calls with `history.pushState()` before the mutation.

However, since both canvas components perform the edge mutation internally (updating `edges` directly), the history push must happen inside `handleReconnect`:

The canvas components do not have direct access to the history manager. Instead, the approach is to add an `onreconnectedge` prop callback that the parent page (`+page.svelte`) handles, similar to `ondeleteedge`. But examining the current architecture, `handleReconnect` in the canvas already mutates edges directly. The cleanest approach without refactoring is to ensure the parent page's handleReconnect callback is used instead, or to add an optional callback prop.

**Selected approach:** Keep `handleReconnect` in the canvas components but have them call `ondeleteedge`-style callbacks. Since the canvas needs to mutate edges in response to the SvelteFlow `onreconnect` event (the library expects edges to update), the canvas `handleReconnect` will be modified to optionally call a new `onreconnectedge` prop before performing the mutation, allowing the parent to push history.

Alternatively (simpler): The parent page (`+page.svelte`) does not pass `onreconnect` to the canvas — the canvas handles it internally. To integrate with undo, we add an `onbeforereconnect` prop to the canvas components that the parent uses to push history state.

**Final approach (simplest):** Add an optional `onreconnectedge` callback prop to ModelCanvas and FullViewCanvas. When present, the canvas calls it before mutating edges. The parent page provides a handler that pushes history. This is consistent with the `ondeleteedge` pattern.

---

## D. Changes to ModelCanvas.svelte and FullViewCanvas.svelte

### New Prop

```typescript
interface Props {
    // ... existing props ...
    onreconnectedge?: (oldEdge: CanvasEdge, newConnection: { source: string; target: string }) => void;
}
```

### Updated handleReconnect

```typescript
function handleReconnect(oldEdge: CanvasEdge, newConnection: { source: string; target: string; sourceHandle?: string | null; targetHandle?: string | null }) {
    onreconnectedge?.(oldEdge, newConnection);
    edges = edges.map((e) =>
        e.id === oldEdge.id
            ? { ...e, source: newConnection.source, target: newConnection.target, sourceHandle: newConnection.sourceHandle ?? undefined, targetHandle: newConnection.targetHandle ?? undefined }
            : e,
    );
    announcer?.announce('Edge reconnected');
}
```

---

## E. Changes to Model Detail Page (+page.svelte)

### New Handler

```typescript
function handleReconnectEdge() {
    history.pushState(canvasNodes, canvasEdges);
    canvasDirty = true;
}
```

### Canvas Component Props

```svelte
<ModelCanvas
    ...
    onreconnectedge={handleReconnectEdge}
/>
```

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Edge endpoints show grab handles on hover | Hover over edge source/target endpoint; verify cursor changes and handle appears |
| Edge can be dragged to new target | Drag edge endpoint to different node; verify edge reconnected |
| Edge reconnection fires onreconnect | Reconnect an edge; verify `handleReconnect` is called |
| Reconnection pushes undo history | Reconnect an edge; press Ctrl+Z; verify edge reverts to original connection |
| Canvas marked dirty after reconnection | Reconnect an edge; verify "Unsaved changes" indicator appears |
| All edge types have reconnect anchors | Verify Simple View (5), UML (6), and ArchiMate (1) edges all have EdgeReconnectAnchor |
| Screen reader announces reconnection | Reconnect an edge; verify "Edge reconnected" announcement |
| Existing edge styling preserved | Verify dash patterns, labels, and ARIA labels unchanged after adding anchors |

---

*This specification implements [ADR-038](../ADR-038-Edge-Reconnection-Fix.md).*
