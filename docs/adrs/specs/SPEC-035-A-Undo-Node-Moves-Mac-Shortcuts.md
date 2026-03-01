# SPEC-035-A: Undo/Redo Node Moves + Mac Shortcut Labels

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-035-A |
| **ADR Reference** | [ADR-035: Undo/Redo Node Moves + Mac Shortcut Labels](../ADR-035-Undo-Redo-Node-Moves-Mac-Shortcuts.md) |
| **Date** | 2026-03-01 |
| **Status** | Active |

---

## Overview

This specification extends the canvas undo/redo system (ADR-028/SPEC-028-A) to cover node drag moves and corrects shortcut labels for cross-platform accuracy. Two changes are required:

1. **Node drag undo:** Push a history snapshot when a node drag begins, so that undo restores the pre-drag positions.
2. **Mac shortcut labels:** Update Undo/Redo button `title` attributes from "Ctrl+Z"/"Ctrl+Y" to "Ctrl/Cmd+Z"/"Ctrl/Cmd+Y".

---

## A. Node Drag Undo

### Event Flow

The `onnodedragstart` event from `<SvelteFlow>` fires once when a user begins dragging a node. This is the correct moment to capture pre-mutation state.

### Props Added

#### ModelCanvas.svelte

Add optional prop to the `Props` interface:

```typescript
onnodedragstart?: () => void;
```

Pass `onnodedragstart` to `<SvelteFlow>` as an event handler that calls the prop:

```svelte
<SvelteFlow
    ...
    onnodedragstart={() => onnodedragstart?.()}
>
```

#### FullViewCanvas.svelte

Identical change: add `onnodedragstart?: () => void` prop and pass to `<SvelteFlow>`.

### Model Detail Page Integration

In `models/[id]/+page.svelte`, define the handler:

```typescript
function handleNodeDragStart() {
    history.pushState(canvasNodes, canvasEdges);
    canvasDirty = true;
}
```

Pass to all `<ModelCanvas>` and `<FullViewCanvas>` instances:

```svelte
<ModelCanvas
    ...
    onnodedragstart={handleNodeDragStart}
/>
```

This must be added to all four canvas instances in the editing blocks (both normal and focus-mode views for both simple and full-view canvas types).

---

## B. Mac Shortcut Labels

### Button Title Updates

In `models/[id]/+page.svelte`, update the two toolbar buttons:

| Button | Old `title` | New `title` |
|--------|-------------|-------------|
| Undo | `Undo (Ctrl+Z)` | `Undo (Ctrl/Cmd+Z)` |
| Redo | `Redo (Ctrl+Y)` | `Redo (Ctrl/Cmd+Y)` |

The keyboard handler (KeyboardHandler.svelte) already uses `event.ctrlKey || event.metaKey` so both Ctrl and Cmd keys work. This change is label-only.

---

## C. Unit Tests

### canvasHistory.test.ts (EXTEND)

Add test cases to the existing `canvasHistory.test.ts`:

1. **`pushState on node drag start enables undo to restore pre-drag positions`** -- Push state with node at position (0,0), then simulate the node being at (100,50), call undo, verify the restored state has node at original (0,0).

2. **`undo after node drag restores original node positions`** -- Push state, move node positions in "current" state, undo, verify restored positions match the pre-drag snapshot.

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Drag node, click Undo: node returns to original position | Manual / E2E test |
| Drag node, Ctrl+Z: node returns to original position | Manual / E2E test |
| Undo button `title` reads "Undo (Ctrl/Cmd+Z)" | Unit test / inspection |
| Redo button `title` reads "Redo (Ctrl/Cmd+Y)" | Unit test / inspection |
| Existing undo/redo tests still pass | `npm run test:unit` |
| No regressions in canvas operations | Full test suite |

---

*This specification implements [ADR-035](../ADR-035-Undo-Redo-Node-Moves-Mac-Shortcuts.md).*
