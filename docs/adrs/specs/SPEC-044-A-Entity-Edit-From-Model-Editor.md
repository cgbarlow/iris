# SPEC-044-A: Entity Edit from Model Editor

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-044-A |
| **ADR Reference** | [ADR-044: Entity Edit from Model Editor](../ADR-044-Entity-Edit-From-Model-Editor.md) |
| **Date** | 2026-03-01 |
| **Status** | Active |

---

## Overview

This specification details the changes required to enable in-context entity editing from the model editor canvas. When a linked entity node is selected in edit mode, an "Edit Entity" button appears in the toolbar. Clicking it fetches the entity from the API, opens the existing `EntityDialog` in edit mode, and on save issues a `PUT` to update the entity before reflecting the changes on the canvas node.

---

## A. Canvas Component Updates

### Node Selection Callback

Add an `onnodeselect` callback prop to both `ModelCanvas` and `FullViewCanvas` so the parent page can track which node is selected:

```typescript
interface Props {
    // ... existing props ...
    onnodeselect?: (nodeId: string | null) => void;
}
```

The canvas components invoke `onnodeselect` in `handleNodeClick` (with the node ID) and in `handleEdgeClick` (with `null`, since edge selection clears node selection).

### Affected Files

| File | Change |
|------|--------|
| `src/lib/canvas/ModelCanvas.svelte` | Add `onnodeselect` prop; call in `handleNodeClick` and `handleEdgeClick` |
| `src/lib/canvas/FullViewCanvas.svelte` | Add `onnodeselect` prop; call in `handleNodeClick` and `handleEdgeClick` |

---

## B. Model Detail Page State

### New State Variables

```typescript
// Edit entity state (WP-15)
let selectedEditNodeId = $state<string | null>(null);
let showEditEntity = $state(false);
let editEntityData = $state<Entity | null>(null);
```

### Node Selection Handler

```typescript
function handleNodeSelect(nodeId: string | null) {
    selectedEditNodeId = nodeId;
}
```

### Derived: Is Selected Node a Linked Entity?

```typescript
const selectedNodeIsLinkedEntity = $derived.by(() => {
    if (!selectedEditNodeId) return false;
    const node = canvasNodes.find((n) => n.id === selectedEditNodeId);
    return !!node?.data?.entityId;
});
```

This derived value controls the visibility of the "Edit Entity" button -- it is `true` only when a node with an `entityId` is selected.

---

## C. Edit Entity Flow

### Step 1: Fetch Entity

When the "Edit Entity" button is clicked, fetch the entity from the API:

```typescript
async function handleEditEntityClick() {
    if (!selectedEditNodeId) return;
    const node = canvasNodes.find((n) => n.id === selectedEditNodeId);
    if (!node?.data?.entityId) return;
    try {
        editEntityData = await apiFetch<Entity>(`/api/entities/${node.data.entityId}`);
        showEditEntity = true;
    } catch (e) {
        error = e instanceof ApiError ? e.message : 'Failed to load entity for editing';
    }
}
```

### Step 2: Show EntityDialog in Edit Mode

A second `EntityDialog` instance is rendered with `mode="edit"` and pre-filled values from the fetched entity:

```svelte
<EntityDialog
    open={showEditEntity}
    mode="edit"
    initialName={editEntityData?.name ?? ''}
    initialType={(editEntityData?.entity_type ?? 'component') as SimpleEntityType}
    initialDescription={editEntityData?.description ?? ''}
    onsave={handleEditEntitySave}
    oncancel={() => { showEditEntity = false; editEntityData = null; }}
/>
```

### Step 3: Save Entity and Update Canvas Node

```typescript
async function handleEditEntitySave(name: string, entityType: SimpleEntityType, description: string) {
    if (!editEntityData || !selectedEditNodeId) return;
    try {
        await apiFetch(`/api/entities/${editEntityData.id}`, {
            method: 'PUT',
            headers: { 'If-Match': String(editEntityData.current_version) },
            body: JSON.stringify({
                name,
                entity_type: entityType,
                description,
                change_summary: 'Updated entity from model editor',
            }),
        });
        canvasNodes = canvasNodes.map((n) =>
            n.id === selectedEditNodeId
                ? { ...n, type: entityType, data: { ...n.data, label: name, entityType, description } }
                : n,
        );
        canvasDirty = true;
        showEditEntity = false;
        editEntityData = null;
    } catch (e) {
        error = e instanceof ApiError ? e.message : 'Failed to update entity';
    }
}
```

---

## D. Toolbar UI

### Edit Entity Button

The button is placed at the start of the "Edit group" section in the canvas toolbar, visible only when `selectedNodeIsLinkedEntity` is true:

```svelte
<!-- Edit group -->
<div class="flex items-center gap-2">
    {#if selectedNodeIsLinkedEntity}
        <button
            onclick={handleEditEntityClick}
            class="rounded px-3 py-1.5 text-sm"
            style="border: 1px solid var(--color-primary); color: var(--color-primary)"
        >
            Edit Entity
        </button>
    {/if}
    <!-- ... existing Delete Edge, Routing, Undo, Redo buttons ... -->
</div>
```

---

## E. Canvas Component Wiring

All four canvas component instances on the page (two in focus mode, two in normal mode) receive the `onnodeselect={handleNodeSelect}` prop:

| Instance | Location |
|----------|----------|
| FullViewCanvas (focus mode) | Inside `<FocusView>` for UML/ArchiMate |
| ModelCanvas (focus mode) | Inside `<FocusView>` for simple/roadmap |
| FullViewCanvas (normal) | Inside 500px container for UML/ArchiMate |
| ModelCanvas (normal) | Inside 500px container for simple/roadmap |

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| "Edit Entity" button visible only when a linked entity node is selected in edit mode | Select a node with `entityId`; verify button appears |
| "Edit Entity" button hidden when no node selected | Click canvas background; verify button disappears |
| "Edit Entity" button hidden for unlinked nodes (no entityId) | Select a node without `entityId`; verify button absent |
| Clicking "Edit Entity" fetches entity from API | Network inspector shows `GET /api/entities/{id}` |
| EntityDialog opens in edit mode with pre-filled data | Verify name, type, and description match the entity |
| Saving updates entity via PUT with If-Match header | Network inspector shows `PUT /api/entities/{id}` with `If-Match` |
| Canvas node label and description update after save | Verify node displays updated name |
| Canvas node type updates after save | Verify node renders with new entity type shape |
| Canvas marked dirty after entity edit save | "Unsaved changes" indicator appears |
| Cancel closes dialog without changes | Click Cancel; verify no API call and no node changes |
| API error displayed on fetch failure | Simulate 404; verify error message shown |
| API error displayed on save failure | Simulate 409 conflict; verify error message shown |

---

*This specification implements [ADR-044](../ADR-044-Entity-Edit-From-Model-Editor.md).*
