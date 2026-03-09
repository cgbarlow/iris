# SPEC-091-A: Node Resizing

**ADR:** ADR-091
**Date:** 2026-03-08

## Changes

### 1. Custom node components — add NodeResizer

Import `NodeResizer` from `@xyflow/svelte` and render it inside each custom node component
(CanvasNode, NavigationCellNode, etc.). Only render when `editMode` is true.

```svelte
{#if editMode}
  <NodeResizer minWidth={80} minHeight={40} />
{/if}
```

### 2. Handle resize events

Listen for the `onResize` / `onResizeEnd` callback on each node. On resize end, dispatch an
update to persist the new `width` and `height` into the node's visual override data
(`node.data.visual.width`, `node.data.visual.height`).

### 3. Persist dimensions via visual override API

Reuse the existing visual override persistence (ADR-085) to save resized dimensions. No new
API endpoints required — the PATCH endpoint for node visual data already accepts width/height.

### 4. Minimum size constraints

Enforce minimum dimensions to prevent nodes from collapsing:
- Default minimum: 80px wide, 40px tall
- Nodes with icons: 48px wide, 48px tall (icon must remain visible)

## Test Plan

- Unit test: NodeResizer renders only in edit mode, hidden in browse mode
- Unit test: resize event updates node dimensions in store
- Integration test: resize persists via visual override API round-trip
