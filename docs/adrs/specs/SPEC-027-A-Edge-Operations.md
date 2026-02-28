# SPEC-027-A: Edge Operations

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-027-A |
| **ADR Reference** | [ADR-027: Edge Selection, Deletion, and Reconnection](../ADR-027-Edge-Selection-Deletion-Reconnection.md) |
| **Date** | 2026-02-28 |
| **Status** | Active |

---

## Overview

This specification covers adding edge selection, deletion, and reconnection capabilities to the Iris canvas. Users will be able to click an edge to select it, delete it via keyboard (Delete/Backspace) or toolbar button, and drag an edge endpoint to reconnect it to a different node.

---

## A. Edge Selection State

### ModelCanvas.svelte and FullViewCanvas.svelte

Add edge selection state and click handler:

```typescript
let selectedEdgeId = $state<string | null>(null);
```

- Clicking an edge sets `selectedEdgeId` and clears `selectedNodeId`
- Clicking a node clears `selectedEdgeId` (already handled by setting `selectedNodeId`)
- Pressing Escape clears both selections
- Screen reader announcement on edge selection: `"Edge selected: {label or type or 'connection'}"`

### Props Extension

```typescript
interface Props {
    // ... existing props ...
    ondeleteedge?: (edgeId: string) => void;  // NEW
}
```

---

## B. Edge Deletion

### Canvas Component Handlers

```typescript
function handleDeleteEdge(edgeId: string) {
    if (ondeleteedge) {
        ondeleteedge(edgeId);
    } else {
        edges = edges.filter((e) => e.id !== edgeId);
    }
    announcer?.announce('Edge deleted');
    selectedEdgeId = null;
}
```

### KeyboardHandler.svelte Extension

Add optional props:

```typescript
selectedEdgeId?: string | null;
ondeleteedge?: (edgeId: string) => void;
```

Extend Delete/Backspace handler to check for selected edges when no node is selected:

```typescript
if (event.key === 'Delete' || event.key === 'Backspace') {
    if (selectedNodeId && !ctrl) {
        event.preventDefault();
        ondelete(selectedNodeId);
    } else if (selectedEdgeId && ondeleteedge && !ctrl) {
        event.preventDefault();
        ondeleteedge(selectedEdgeId);
    }
    return;
}
```

### Model Detail Page Toolbar

Add a "Delete Edge" button in the canvas toolbar (after "Link Entity", before "Save"):

```svelte
<button
    onclick={() => selectedEdgeId && handleDeleteEdge(selectedEdgeId)}
    disabled={!selectedEdgeId}
    class="rounded px-3 py-1.5 text-sm disabled:opacity-50"
    style="border: 1px solid var(--color-danger); color: var(--color-danger)"
>
    Delete Edge
</button>
```

---

## C. Edge Reconnection

### SvelteFlow Configuration

Enable reconnection on the `<SvelteFlow>` component:

```svelte
<SvelteFlow
    edgesReconnectable
    onreconnect={handleReconnect}
    ...
>
```

### Reconnect Handler

```typescript
function handleReconnect(
    oldEdge: CanvasEdge,
    newConnection: { source: string; target: string; sourceHandle?: string; targetHandle?: string }
) {
    edges = edges.map((e) =>
        e.id === oldEdge.id
            ? {
                ...e,
                source: newConnection.source,
                target: newConnection.target,
                sourceHandle: newConnection.sourceHandle,
                targetHandle: newConnection.targetHandle,
            }
            : e,
    );
    announcer?.announce('Edge reconnected');
}
```

The relationship type and data are preserved from the original edge.

---

## D. Selected Edge Styling

Add CSS in `app.css`:

```css
.svelte-flow .svelte-flow__edge.selected path {
    stroke-width: 3;
    stroke: var(--color-primary);
}
```

---

## E. Keyboard Interaction Summary

| Key | With Node Selected | With Edge Selected | No Selection |
|-----|-------------------|-------------------|--------------|
| Delete/Backspace | Delete node | Delete edge | No action |
| Escape | Deselect node | Deselect edge | No action |
| Tab | Navigate nodes | Navigate nodes | Select first node |

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Edge click selects edge | Click an edge; verify visual selection highlight (stroke-width 3, primary colour) |
| Edge click deselects node | Select a node, then click an edge; verify node is deselected |
| Node click deselects edge | Select an edge, then click a node; verify edge is deselected |
| Delete key removes edge | Select an edge, press Delete; verify edge removed and screen reader announced |
| Backspace key removes edge | Select an edge, press Backspace; verify edge removed |
| Delete Edge button works | Select an edge; verify "Delete Edge" button enabled; click it; verify edge removed |
| Delete Edge button disabled when no edge selected | Verify "Delete Edge" button is disabled when no edge is selected |
| Edge reconnection works | Hover over edge endpoint; drag to different node; verify edge reconnected |
| Edge deletion does not delete nodes | Select and delete an edge; verify both connected nodes remain |
| Escape clears edge selection | Select an edge, press Escape; verify selection cleared |
| Changes marked as dirty | Delete or reconnect an edge; verify canvas shows "Unsaved changes" |

---

*This specification implements [ADR-027](../ADR-027-Edge-Selection-Deletion-Reconnection.md).*
