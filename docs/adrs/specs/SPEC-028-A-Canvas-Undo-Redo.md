# SPEC-028-A: Canvas Undo/Redo Implementation

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-028-A |
| **ADR Reference** | [ADR-028: Canvas Undo/Redo](../ADR-028-Canvas-Undo-Redo.md) |
| **Date** | 2026-02-28 |
| **Status** | Active |

---

## Overview

This specification covers the implementation of client-side undo/redo for canvas operations. The feature uses a snapshot-based history manager built with Svelte 5 runes, integrated into the model detail page with toolbar buttons and keyboard shortcuts.

---

## A. History Manager Module

### useCanvasHistory.svelte.ts (NEW)

**Location:** `frontend/src/lib/canvas/useCanvasHistory.svelte.ts`

Svelte 5 runes module providing undo/redo stack management:

- **Constants:** `MAX_HISTORY = 50` — upper bound on undo stack depth
- **State:** `undoStack: HistoryEntry[]`, `redoStack: HistoryEntry[]` (both `$state`)
- **Interface:** `HistoryEntry { nodes: CanvasNode[]; edges: CanvasEdge[] }`
- **Methods:**
  - `pushState(nodes, edges)` — Deep-clone current state onto undo stack; clear redo stack; trim to MAX_HISTORY
  - `undo(currentNodes, currentEdges)` — Pop from undo stack, push current state to redo stack, return previous state (or null if empty)
  - `redo(currentNodes, currentEdges)` — Pop from redo stack, push current state to undo stack, return next state (or null if empty)
  - `clear()` — Reset both stacks (called on save/discard)
- **Getters:**
  - `canUndo` — `undoStack.length > 0`
  - `canRedo` — `redoStack.length > 0`

All snapshots use `structuredClone()` for deep isolation.

---

## B. Model Detail Page Integration

### Import and Initialisation

- Import `createCanvasHistory` from `$lib/canvas/useCanvasHistory.svelte`
- Instantiate `const history = createCanvasHistory()` alongside canvas state declarations

### Pre-Mutation Snapshots

Call `history.pushState(canvasNodes, canvasEdges)` immediately before each canvas mutation:

| Function | Mutation |
|----------|---------|
| `handleAddEntity()` | `canvasNodes = [...canvasNodes, newNode]` |
| `handleDeleteNode()` | `canvasNodes = canvasNodes.filter(...)` |
| `handleRelationshipSave()` | `canvasEdges = [...canvasEdges, newEdge]` |
| `handleLinkEntity()` | `canvasNodes = [...canvasNodes, newNode]` |

### Undo/Redo Handlers

```typescript
function handleUndo() {
    const state = history.undo(canvasNodes, canvasEdges);
    if (state) {
        canvasNodes = state.nodes;
        canvasEdges = state.edges;
        canvasDirty = true;
    }
}

function handleRedo() {
    const state = history.redo(canvasNodes, canvasEdges);
    if (state) {
        canvasNodes = state.nodes;
        canvasEdges = state.edges;
        canvasDirty = true;
    }
}
```

### History Clearing

- `discardChanges()` — call `history.clear()` after `parseCanvasData()`
- `saveCanvas()` — call `history.clear()` after successful save (before `loadModel`)

### Toolbar Buttons

Add Undo and Redo buttons to the canvas editing toolbar, positioned after "Link Entity" and before "Save":

- **Undo:** `disabled={!history.canUndo}`, `aria-label="Undo"`, `title="Undo (Ctrl+Z)"`
- **Redo:** `disabled={!history.canRedo}`, `aria-label="Redo"`, `title="Redo (Ctrl+Y)"`
- Both use the same styling as existing toolbar buttons (border, rounded, text-sm)

---

## C. Keyboard Shortcuts

### KeyboardHandler.svelte (MODIFY)

Add optional props:
- `onundo?: () => void`
- `onredo?: () => void`

In the `if (ctrl)` block of `handleKeydown`, add handlers:
- `Ctrl+Z` — call `onundo()` if provided
- `Ctrl+Y` — call `onredo()` if provided

### ModelCanvas.svelte (MODIFY)

Add optional props `onundo` and `onredo`, pass through to `KeyboardHandler`.

### FullViewCanvas.svelte (MODIFY)

Add optional props `onundo` and `onredo`, pass through to `KeyboardHandler`.

### Model Detail Page (MODIFY)

Pass `onundo={handleUndo}` and `onredo={handleRedo}` to all `ModelCanvas` and `FullViewCanvas` instances.

---

## D. Unit Tests

### canvasHistory.test.ts (NEW)

**Location:** `frontend/tests/unit/canvasHistory.test.ts`

Test cases:
- Starts with empty stacks (canUndo/canRedo both false)
- pushState enables undo
- undo restores previous state
- redo restores undone state
- New action after undo clears redo stack
- Returns null when nothing to undo
- Returns null when nothing to redo

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Undo button enabled after adding entity | Add entity; verify Undo button is not disabled |
| Undo restores previous state | Add entity then click Undo; verify entity removed from canvas |
| Redo restores undone state | Undo an add; click Redo; verify entity reappears |
| New action clears redo | Undo, then add new entity; verify Redo button disabled |
| Ctrl+Z triggers undo | Add entity, press Ctrl+Z; verify entity removed |
| Ctrl+Y triggers redo | Undo, press Ctrl+Y; verify entity restored |
| History cleared on save | Save canvas; verify Undo button disabled |
| History cleared on discard | Discard changes; verify Undo button disabled |
| Max history bounded | Perform 60 operations; verify only last 50 are undoable |
| Unit tests pass | Run `npm run test:unit`; all canvasHistory tests green |

---

*This specification implements [ADR-028](../ADR-028-Canvas-Undo-Redo.md).*
