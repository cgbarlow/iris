# SPEC-042-A: Connector Manipulation

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-042-A |
| **ADR Reference** | [ADR-042: Connector Manipulation](../ADR-042-Connector-Manipulation.md) |
| **Date** | 2026-03-01 |
| **Status** | Active |

---

## Overview

This specification details the changes required to enable per-edge routing type selection in the Iris canvas. Users can select an edge in edit mode and choose a routing type (Default, Straight, Step, Smooth Step, Bezier) from a toolbar dropdown. The routing type is stored in `CanvasEdgeData` and persisted with the model.

---

## A. Canvas Types Update

### CanvasEdgeData Interface

Add optional `routingType` field to `frontend/src/lib/types/canvas.ts`:

```typescript
/** Routing algorithm for edge path rendering. */
export type EdgeRoutingType = 'default' | 'straight' | 'step' | 'smoothstep' | 'bezier';

/** Data stored in each canvas edge. */
export interface CanvasEdgeData {
    relationshipType: SimpleRelationshipType;
    relationshipId?: string;
    label?: string;
    routingType?: EdgeRoutingType;
    [key: string]: unknown;
}
```

---

## B. Edge Component Updates

### Path Function Selection

Each of the 5 Simple View edge components must read `data.routingType` and select the appropriate path function:

| Routing Type | Path Function | Notes |
|-------------|--------------|-------|
| `'default'` or `undefined` | Keep existing behavior (`getBezierPath`) | No change to current rendering |
| `'straight'` | `getStraightPath` | Direct line between source and target |
| `'step'` | `getSmoothStepPath` with `borderRadius: 0` | Right-angle steps with sharp corners |
| `'smoothstep'` | `getSmoothStepPath` | Right-angle steps with rounded corners (default borderRadius) |
| `'bezier'` | `getBezierPath` | Cubic bezier curve |

### Import Changes

Each edge component must import the additional path functions:

```typescript
import {
    BaseEdge,
    EdgeReconnectAnchor,
    getBezierPath,
    getStraightPath,
    getSmoothStepPath,
    type EdgeProps,
} from '@xyflow/svelte';
```

### Path Computation

Replace the single `getBezierPath` call with a routing-type-aware `$derived`:

```typescript
const pathParams = { sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition };

const path = $derived.by(() => {
    const rt = data?.routingType;
    if (rt === 'straight') return getStraightPath(pathParams);
    if (rt === 'step') return getSmoothStepPath({ ...pathParams, borderRadius: 0 });
    if (rt === 'smoothstep') return getSmoothStepPath(pathParams);
    if (rt === 'bezier') return getBezierPath(pathParams);
    return getBezierPath(pathParams); // default
});
```

### Affected Files

| File | Edge Type |
|------|-----------|
| `src/lib/canvas/edges/UsesEdge.svelte` | uses |
| `src/lib/canvas/edges/DependsOnEdge.svelte` | depends_on |
| `src/lib/canvas/edges/ComposesEdge.svelte` | composes |
| `src/lib/canvas/edges/ImplementsEdge.svelte` | implements |
| `src/lib/canvas/edges/ContainsEdge.svelte` | contains |

---

## C. Model Detail Page Updates

### Edge Selection Communication

Add an `onedgeselect` callback prop to `ModelCanvas` and `FullViewCanvas` so the parent page knows which edge is selected:

```typescript
interface Props {
    // ... existing props ...
    onedgeselect?: (edgeId: string | null) => void;
}
```

The canvas components call `onedgeselect` whenever `selectedEdgeId` changes (in `handleEdgeClick`, `handleNodeClick`, etc.).

### Routing Type Dropdown

When an edge is selected in edit mode, show a routing type `<select>` in the toolbar "Edit group" area:

```svelte
{#if selectedEdgeId}
    <label class="flex items-center gap-1 text-sm" style="color: var(--color-fg)">
        Routing:
        <select
            value={selectedEdgeRoutingType}
            onchange={handleRoutingTypeChange}
            class="rounded px-2 py-1 text-sm"
            style="border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-fg)"
            aria-label="Edge routing type"
        >
            <option value="default">Default</option>
            <option value="straight">Straight</option>
            <option value="step">Step</option>
            <option value="smoothstep">Smooth Step</option>
            <option value="bezier">Bezier</option>
        </select>
    </label>
{/if}
```

### Routing Type Change Handler

```typescript
function handleRoutingTypeChange(event: Event) {
    const target = event.target as HTMLSelectElement;
    const newType = target.value as EdgeRoutingType;
    if (!selectedEdgeId) return;
    history.pushState(canvasNodes, canvasEdges);
    canvasEdges = canvasEdges.map((e) =>
        e.id === selectedEdgeId
            ? { ...e, data: { ...e.data!, routingType: newType === 'default' ? undefined : newType } }
            : e,
    );
    canvasDirty = true;
}
```

### Derived Routing Type for Display

```typescript
const selectedEdgeRoutingType = $derived.by(() => {
    if (!selectedEdgeId) return 'default';
    const edge = canvasEdges.find((e) => e.id === selectedEdgeId);
    return edge?.data?.routingType ?? 'default';
});
```

---

## D. Persistence

The routing type is stored in `CanvasEdgeData` which is already serialized as part of the model's `data.edges` array. No backend changes are needed — the existing `PUT /api/models/{id}` endpoint handles the JSON blob.

---

## E. Undo/Redo Integration

Routing type changes push the current state to the undo history before modification, using the same `history.pushState(canvasNodes, canvasEdges)` pattern as other canvas mutations.

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| `CanvasEdgeData` includes optional `routingType` field | Type check passes |
| `EdgeRoutingType` type exported from canvas types | Import in test file succeeds |
| Routing type dropdown visible when edge selected in edit mode | Select edge in edit mode; verify dropdown appears |
| Routing type dropdown hidden when no edge selected | Deselect edge; verify dropdown disappears |
| Changing routing type updates edge path rendering | Change to "Straight"; verify path changes |
| Routing type change pushes undo state | Change routing type; press Ctrl+Z; verify revert |
| Routing type change marks canvas dirty | Change routing type; verify "Unsaved changes" appears |
| Routing type persists through save/reload | Change routing type, save, reload; verify retained |
| All 5 Simple View edges support all routing types | File inspection: all edges import all path functions |
| Default routing type preserves existing behavior | Edge with no routingType renders as bezier (existing default) |

---

*This specification implements [ADR-042](../ADR-042-Connector-Manipulation.md).*
