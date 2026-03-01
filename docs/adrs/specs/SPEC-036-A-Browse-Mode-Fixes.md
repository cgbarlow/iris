# SPEC-036-A: Browse Mode Fixes Implementation

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-036-A |
| **ADR Reference** | [ADR-036: Browse Mode Fixes](../ADR-036-Browse-Mode-Fixes.md) |
| **Date** | 2026-03-01 |
| **Status** | Active |

---

## Overview

This specification covers two browse mode fixes: (a) the "Used In Models" list in EntityDetailPanel now shows all models including the current one (marked with "(current)"), and (b) canvas entity nodes in browse mode show a hover overlay link for direct navigation to the entity detail page.

---

## Fix A: Used In Models — Show All Models

### Current Behaviour (Bug)

In `EntityDetailPanel.svelte`, the template iterates over `usedInModels` and filters with:

```svelte
{#if model.model_id !== currentModelId}
```

When an entity is only used in the current model, this filter removes the only entry, resulting in an empty list and the message "Not used in any other models."

### Required Change

1. Remove the `{#if model.model_id !== currentModelId}` conditional.
2. Show all models returned by the API.
3. When `model.model_id === currentModelId`, append a "(current)" label next to the model name.
4. Update the empty-state message from "Not used in any other models." to "Not used in any models."

### Template Change

```svelte
{#each usedInModels as model}
    <li>
        <a href="/models/{model.model_id}" ...>
            {model.name}
            {#if model.model_id === currentModelId}
                <span class="text-xs" style="color: var(--color-muted)">(current)</span>
            {/if}
            <span class="text-xs" style="color: var(--color-muted)">({model.model_type})</span>
        </a>
    </li>
{/each}
```

---

## Fix B: Browse Mode Node Navigation Overlay

### Approach

1. Add a `browseMode` boolean field to `CanvasNodeData`.
2. In `BrowseCanvas.svelte`, set `browseMode: true` in each node's data before passing to SvelteFlow.
3. In each Simple View node component, when `data.browseMode` is true and `data.entityId` is present, render an absolute-positioned `<a>` element that appears on `:hover`.

### CanvasNodeData Change

Add to the `CanvasNodeData` interface in `canvas.ts`:

```typescript
browseMode?: boolean;
```

### BrowseCanvas Change

Before passing nodes to SvelteFlow, map them to include `browseMode: true`:

```typescript
const browseNodes = $derived(
    nodes.map(n => ({
        ...n,
        data: { ...n.data, browseMode: true }
    }))
);
```

### Node Component Change (all 7 node types)

Add a hover overlay link inside the `.canvas-node` div:

```svelte
{#if data.browseMode && data.entityId}
    <a
        href="/entities/{data.entityId}"
        class="canvas-node__browse-link"
        aria-label="View {data.label} details"
    >
        View details
    </a>
{/if}
```

### CSS for Hover Overlay

```css
.canvas-node__browse-link {
    display: none;
    position: absolute;
    bottom: -2px;
    right: -2px;
    padding: 2px 8px;
    border-radius: 4px;
    background: var(--color-primary);
    color: #fff;
    font-size: 0.65rem;
    font-weight: 600;
    text-decoration: none;
    z-index: 5;
    white-space: nowrap;
}

.canvas-node:hover .canvas-node__browse-link {
    display: block;
}
```

---

## Files Modified

| File | Change |
|------|--------|
| `frontend/src/lib/types/canvas.ts` | Add `browseMode?: boolean` to `CanvasNodeData` |
| `frontend/src/lib/canvas/controls/EntityDetailPanel.svelte` | Remove current-model filter, add "(current)" label, update empty message |
| `frontend/src/lib/canvas/BrowseCanvas.svelte` | Map nodes to include `browseMode: true` |
| `frontend/src/lib/canvas/nodes/ComponentNode.svelte` | Add browse link overlay |
| `frontend/src/lib/canvas/nodes/ServiceNode.svelte` | Add browse link overlay |
| `frontend/src/lib/canvas/nodes/InterfaceNode.svelte` | Add browse link overlay |
| `frontend/src/lib/canvas/nodes/PackageNode.svelte` | Add browse link overlay |
| `frontend/src/lib/canvas/nodes/ActorNode.svelte` | Add browse link overlay |
| `frontend/src/lib/canvas/nodes/DatabaseNode.svelte` | Add browse link overlay |
| `frontend/src/lib/canvas/nodes/QueueNode.svelte` | Add browse link overlay |
| `frontend/src/app.css` | Add `.canvas-node__browse-link` styles |
| `frontend/tests/unit/browseModeFixes.test.ts` | Unit tests for both fixes |

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Entity used only in current model shows "(current)" in Used In Models list | Select entity in browse mode; verify current model appears with "(current)" label |
| Entity used in multiple models shows all models | Select entity in browse mode; verify all models listed, current model marked "(current)" |
| Entity not used in any model shows "Not used in any models." | Select entity with no model usage; verify empty-state message |
| Hovering a browse-mode node shows "View details" link | Hover over entity node in browse mode; verify link overlay appears |
| Browse link navigates to entity detail page | Click "View details" overlay; verify navigation to `/entities/{entityId}` |
| Browse link has correct aria-label | Inspect overlay link; verify `aria-label="View {label} details"` |
| Nodes without entityId do not show browse link | Hover node without entityId; verify no overlay appears |
| Edit mode nodes do not show browse link | Edit canvas; hover node; verify no overlay appears |

---

*This specification implements [ADR-036](../ADR-036-Browse-Mode-Fixes.md).*
