# SPEC-048-A: Edge Label System

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-048-A |
| **ADR Reference** | [ADR-048: Edge Label System](../ADR-048-Edge-Label-System.md) |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## Overview

This specification details the shared EdgeLabel component for inline edge label editing, DOMPurify sanitisation, and drag-to-reposition functionality. The component uses @xyflow/svelte's `EdgeLabelRenderer` for DOM-based label rendering positioned along edge paths, with double-click editing and pointer-event-based repositioning.

---

## A. EdgeLabel Component

### Component File

**File:** `src/lib/canvas/edges/EdgeLabel.svelte`

### Props

```typescript
interface Props {
    label: string;
    labelX: number;
    labelY: number;
    labelOffsetX?: number;
    labelOffsetY?: number;
    labelRotation?: number;
    editable?: boolean;
    edgeId: string;
}
```

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `label` | `string` | required | The display text for the edge label |
| `labelX` | `number` | required | Base X position from @xyflow edge path calculation |
| `labelY` | `number` | required | Base Y position from @xyflow edge path calculation |
| `labelOffsetX` | `number` | `0` | User-applied X offset from drag repositioning |
| `labelOffsetY` | `number` | `0` | User-applied Y offset from drag repositioning |
| `labelRotation` | `number` | `0` | Rotation in degrees (reserved for future use) |
| `editable` | `boolean` | `false` | Whether double-click editing is enabled (edit mode only) |
| `edgeId` | `string` | required | The parent edge ID, used in dispatched events |

### Rendering

The component renders inside `<EdgeLabelRenderer>` from `@xyflow/svelte`, which places DOM elements in a layer above the SVG canvas:

```svelte
<script lang="ts">
    import { EdgeLabelRenderer } from '@xyflow/svelte';
    import DOMPurify from 'dompurify';

    let { label, labelX, labelY, labelOffsetX = 0, labelOffsetY = 0,
          labelRotation = 0, editable = false, edgeId }: Props = $props();

    let editing = $state(false);
    let editValue = $state(label);

    const posX = $derived(labelX + labelOffsetX);
    const posY = $derived(labelY + labelOffsetY);
</script>

<EdgeLabelRenderer>
    <div
        class="edge-label"
        style="position: absolute; transform: translate(-50%, -50%) translate({posX}px, {posY}px) rotate({labelRotation}deg); pointer-events: all;"
    >
        {#if editing}
            <input
                type="text"
                bind:value={editValue}
                onblur={commitEdit}
                onkeydown={handleKeydown}
                class="edge-label-input"
            />
        {:else}
            <span
                ondblclick={editable ? startEdit : undefined}
                onpointerdown={editable ? startDrag : undefined}
                class="edge-label-text"
            >
                {label}
            </span>
        {/if}
    </div>
</EdgeLabelRenderer>
```

---

## B. Double-Click Inline Editing

### Edit Flow

1. User double-clicks the label text in edit mode
2. Label text is replaced with an `<input>` element pre-filled with the current value
3. Input receives focus automatically
4. User modifies the text
5. On blur or Enter key, the edit is committed
6. On Escape, the edit is cancelled and original value restored

### Edit Functions

```typescript
function startEdit() {
    if (!editable) return;
    editing = true;
    editValue = label;
    // Focus input on next tick
    tick().then(() => {
        const input = document.querySelector('.edge-label-input') as HTMLInputElement;
        input?.focus();
        input?.select();
    });
}

function commitEdit() {
    editing = false;
    const sanitised = DOMPurify.sanitize(editValue.trim(), { ALLOWED_TAGS: [] });
    if (sanitised && sanitised !== label) {
        const event = new CustomEvent('edgelabeledit', {
            detail: { edgeId, label: sanitised },
            bubbles: true,
        });
        document.dispatchEvent(event);
    }
}

function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') {
        e.preventDefault();
        commitEdit();
    } else if (e.key === 'Escape') {
        editing = false;
        editValue = label;
    }
}
```

### DOMPurify Sanitisation

All user-entered label text is sanitised with `DOMPurify.sanitize()` using `{ ALLOWED_TAGS: [] }` to strip all HTML, ensuring only plain text is stored. This follows the established input sanitisation pattern used throughout the application.

---

## C. CustomEvent Dispatch

### edgelabeledit Event

Dispatched when a label edit is committed with a changed value.

```typescript
new CustomEvent('edgelabeledit', {
    detail: {
        edgeId: string;   // The edge whose label was edited
        label: string;    // The new sanitised label text
    },
    bubbles: true,
});
```

### edgelabelmove Event

Dispatched when a label is repositioned via drag.

```typescript
new CustomEvent('edgelabelmove', {
    detail: {
        edgeId: string;       // The edge whose label was moved
        labelOffsetX: number; // New X offset
        labelOffsetY: number; // New Y offset
    },
    bubbles: true,
});
```

### Event Handling in Canvas

The parent canvas component (`ModelCanvas`, `FullViewCanvas`) listens for these events and updates the corresponding edge data:

```typescript
function handleEdgeLabelEdit(e: CustomEvent) {
    const { edgeId, label } = e.detail;
    canvasEdges = canvasEdges.map((edge) =>
        edge.id === edgeId
            ? { ...edge, data: { ...edge.data, label } }
            : edge
    );
    canvasDirty = true;
}

function handleEdgeLabelMove(e: CustomEvent) {
    const { edgeId, labelOffsetX, labelOffsetY } = e.detail;
    canvasEdges = canvasEdges.map((edge) =>
        edge.id === edgeId
            ? { ...edge, data: { ...edge.data, labelOffsetX, labelOffsetY } }
            : edge
    );
    canvasDirty = true;
}
```

---

## D. CanvasEdgeData Extension

### New Fields

The `CanvasEdgeData` type is extended with three optional fields for label positioning:

**File:** `src/lib/canvas/types.ts`

```typescript
export interface CanvasEdgeData {
    relationshipType: string;
    label?: string;
    routingType?: RoutingType;
    // Edge label positioning (WP-4)
    labelOffsetX?: number;
    labelOffsetY?: number;
    labelRotation?: number;
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `labelOffsetX` | `number` | `0` | Horizontal offset from the edge midpoint |
| `labelOffsetY` | `number` | `0` | Vertical offset from the edge midpoint |
| `labelRotation` | `number` | `0` | Rotation in degrees (future use) |

These fields are persisted as part of the model's canvas data JSON.

---

## E. Drag-to-Reposition

### Pointer Event Handling

Label repositioning uses pointer events for cross-device compatibility (mouse and touch):

```typescript
let dragging = $state(false);
let dragStartX = 0;
let dragStartY = 0;
let dragStartOffsetX = 0;
let dragStartOffsetY = 0;

function startDrag(e: PointerEvent) {
    if (!editable || editing) return;
    dragging = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    dragStartOffsetX = labelOffsetX;
    dragStartOffsetY = labelOffsetY;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    e.preventDefault();
}

function onPointerMove(e: PointerEvent) {
    if (!dragging) return;
    const dx = e.clientX - dragStartX;
    const dy = e.clientY - dragStartY;
    labelOffsetX = dragStartOffsetX + dx;
    labelOffsetY = dragStartOffsetY + dy;
}

function onPointerUp(e: PointerEvent) {
    if (!dragging) return;
    dragging = false;
    const event = new CustomEvent('edgelabelmove', {
        detail: { edgeId, labelOffsetX, labelOffsetY },
        bubbles: true,
    });
    document.dispatchEvent(event);
}
```

### Interaction Discrimination

- **Single click:** No action (allows edge selection)
- **Double click:** Enter edit mode
- **Pointer down + drag:** Reposition the label
- **Pointer down without move + up:** Treated as click (no reposition event dispatched unless offset changed)

---

## F. Edge Component Integration

All five edge components must render the shared `EdgeLabel` when a label is present:

| Edge Component | File |
|----------------|------|
| Uses | `src/lib/canvas/edges/Uses.svelte` |
| DependsOn | `src/lib/canvas/edges/DependsOn.svelte` |
| Composes | `src/lib/canvas/edges/Composes.svelte` |
| Implements | `src/lib/canvas/edges/Implements.svelte` |
| Contains | `src/lib/canvas/edges/Contains.svelte` |

Each edge component includes `EdgeLabel` conditionally:

```svelte
{#if data?.label}
    <EdgeLabel
        label={data.label}
        {labelX}
        {labelY}
        labelOffsetX={data.labelOffsetX ?? 0}
        labelOffsetY={data.labelOffsetY ?? 0}
        labelRotation={data.labelRotation ?? 0}
        editable={$canvasMode === 'edit'}
        {edgeId}
    />
{/if}
```

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| EdgeLabel renders at edge midpoint | Create edge with label; verify label positioned at path midpoint |
| Double-click opens inline editor | Double-click label in edit mode; verify input field appears |
| Enter commits label edit | Type new text, press Enter; verify label updated |
| Escape cancels label edit | Type new text, press Escape; verify original label restored |
| Blur commits label edit | Type new text, click away; verify label updated |
| DOMPurify strips HTML from input | Enter `<script>alert(1)</script>`; verify sanitised to plain text |
| edgelabeledit event dispatched | Monitor events; verify event fires with edgeId and new label |
| Canvas marks dirty after label edit | Edit a label; verify unsaved changes indicator |
| Drag repositions label | Drag label away from midpoint; verify new position |
| edgelabelmove event dispatched | Drag label; verify event fires with edgeId and offsets |
| Label offset persisted in model data | Save model; reload; verify label at repositioned location |
| labelRotation stored in CanvasEdgeData | Verify field exists in type definition and persists |
| All 5 edge types render EdgeLabel | Add label to each edge type; verify label displays |
| Labels not editable in browse mode | Double-click label in browse mode; verify no edit input |

---

*This specification implements [ADR-048](../ADR-048-Edge-Label-System.md).*
