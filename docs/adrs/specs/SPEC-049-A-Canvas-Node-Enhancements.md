# SPEC-049-A: Canvas Node Enhancements

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-049-A |
| **ADR Reference** | [ADR-049: Canvas Node Enhancements](../ADR-049-Canvas-Node-Enhancements.md) |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## Overview

This specification details two canvas node enhancements: (WP-5) automatic description synchronisation from linked entities after canvas load, and (WP-8) a visual differentiation component for model-in-model reference nodes using a stacked-squares visual pattern.

---

## A. Node Description Refresh (WP-5)

### Purpose

When a canvas is loaded, node labels and descriptions may be stale if the linked entity was updated outside the canvas editor. The `refreshNodeDescriptions()` function fetches current entity data for all linked nodes and updates their display data.

### Function Signature

**File:** `src/lib/canvas/canvas-utils.ts` (or co-located utility)

```typescript
export async function refreshNodeDescriptions(
    nodes: CanvasNode[]
): Promise<CanvasNode[]>
```

### Implementation

```typescript
import { apiFetch } from '$lib/utils/api';

interface EntitySummary {
    id: string;
    name: string;
    entity_type: string;
    description: string;
}

export async function refreshNodeDescriptions(
    nodes: CanvasNode[]
): Promise<CanvasNode[]> {
    // Collect nodes with linked entities
    const linkedNodes = nodes.filter((n) => n.data?.entityId);
    if (linkedNodes.length === 0) return nodes;

    // Fetch all entities in parallel
    const entityPromises = linkedNodes.map((n) =>
        apiFetch<EntitySummary>(`/api/entities/${n.data.entityId}`)
            .then((entity) => ({ nodeId: n.id, entity }))
            .catch(() => null) // Skip failed fetches (deleted entities)
    );

    const results = await Promise.all(entityPromises);

    // Build lookup map
    const entityMap = new Map<string, EntitySummary>();
    for (const result of results) {
        if (result) {
            entityMap.set(result.nodeId, result.entity);
        }
    }

    // Update nodes with fresh data
    return nodes.map((node) => {
        const entity = entityMap.get(node.id);
        if (!entity) return node;
        return {
            ...node,
            data: {
                ...node.data,
                label: entity.name,
                entityType: entity.entity_type,
                description: entity.description,
            },
        };
    });
}
```

### Key Design Decisions

- **Promise.all for parallel fetches:** All entity fetches run concurrently rather than sequentially, minimising total load time
- **Graceful error handling:** If a linked entity has been deleted or the fetch fails, the node retains its existing data (the `.catch(() => null)` swallows individual failures)
- **No canvas dirty flag:** Refreshing descriptions does not set `canvasDirty` because this is a read-only sync, not a user edit

### Integration Point

Called after canvas data is loaded and nodes are initialised:

**File:** `src/routes/models/[id]/+page.svelte`

```typescript
// After loading canvas data
canvasNodes = parseCanvasNodes(modelData);
canvasNodes = await refreshNodeDescriptions(canvasNodes);
```

---

## B. ModelRefNode Component (WP-8)

### Purpose

When a model contains a reference to another model (model-in-model composition), the reference node should be visually distinct from entity nodes. The `ModelRefNode` uses a stacked-squares visual pattern to indicate that the node represents a nested model.

### Component File

**File:** `src/lib/canvas/nodes/ModelRefNode.svelte`

### Props

```typescript
interface Props {
    id: string;
    data: {
        label: string;
        modelId: string;
        description?: string;
    };
}
```

### Visual Design

The stacked-squares pattern uses two offset rectangles behind the main node body to create a visual stack effect:

```svelte
<script lang="ts">
    import { Handle, Position } from '@xyflow/svelte';

    let { id, data }: Props = $props();
</script>

<div class="model-ref-node">
    <!-- Stacked squares (back layers) -->
    <div class="stack-layer stack-2"></div>
    <div class="stack-layer stack-1"></div>

    <!-- Main node body -->
    <div class="node-body">
        <div class="node-header">
            <span class="node-icon">&#x25A3;</span>
            <span class="node-label">{data.label}</span>
        </div>
        {#if data.description}
            <div class="node-description">{data.description}</div>
        {/if}
        <a
            href="/models/{data.modelId}"
            class="view-model-link"
            onclick={(e) => e.stopPropagation()}
        >
            View model
        </a>
    </div>

    <!-- Connection handles -->
    <Handle type="target" position={Position.Top} />
    <Handle type="source" position={Position.Bottom} />
    <Handle type="target" position={Position.Left} />
    <Handle type="source" position={Position.Right} />
</div>

<style>
    .model-ref-node {
        position: relative;
        width: 180px;
    }

    .stack-layer {
        position: absolute;
        width: 100%;
        height: 100%;
        border: 1px solid var(--color-border);
        border-radius: 6px;
        background: var(--color-surface);
    }

    .stack-2 {
        top: 6px;
        left: 6px;
    }

    .stack-1 {
        top: 3px;
        left: 3px;
    }

    .node-body {
        position: relative;
        padding: 10px;
        border: 2px solid var(--color-primary);
        border-radius: 6px;
        background: var(--color-surface);
    }

    .node-header {
        display: flex;
        align-items: center;
        gap: 6px;
        font-weight: 600;
        font-size: 0.875rem;
    }

    .node-icon {
        font-size: 1rem;
        color: var(--color-primary);
    }

    .node-description {
        font-size: 0.75rem;
        color: var(--color-text-secondary);
        margin-top: 4px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .view-model-link {
        display: block;
        margin-top: 8px;
        font-size: 0.75rem;
        color: var(--color-primary);
        text-decoration: underline;
    }

    .view-model-link:hover {
        opacity: 0.8;
    }
</style>
```

### Node Type Registration

Register `ModelRefNode` as the `'modelref'` node type in the canvas node types map:

**File:** `src/lib/canvas/node-types.ts` (or equivalent registration file)

```typescript
import ModelRefNode from './nodes/ModelRefNode.svelte';

export const nodeTypes = {
    // ... existing node types ...
    modelref: ModelRefNode,
};
```

### "View model" Link

The "View model" link navigates to the referenced model's detail page (`/models/{modelId}`). The `onclick` handler calls `e.stopPropagation()` to prevent the click from triggering node selection, allowing standard anchor navigation.

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| `refreshNodeDescriptions` fetches entities in parallel | Monitor network; verify concurrent requests (not sequential) |
| Node labels update after refresh | Edit entity name outside canvas, reload canvas; verify node label updated |
| Node descriptions update after refresh | Edit entity description, reload canvas; verify node description updated |
| Deleted entity nodes retain original data | Delete a linked entity, reload canvas; verify node still displays old data |
| Canvas not marked dirty after refresh | Reload canvas; verify no "unsaved changes" indicator |
| ModelRefNode renders stacked-squares visual | Add modelref node; verify two stacked layers behind main body |
| ModelRefNode shows label | Verify label text displayed in node header |
| ModelRefNode shows description | Add description; verify truncated text below header |
| "View model" link navigates to model detail | Click link; verify navigation to `/models/{modelId}` |
| "View model" click does not select node | Click link; verify node selection does not change |
| ModelRefNode registered as 'modelref' type | Create node with `type: 'modelref'`; verify it renders correctly |
| ModelRefNode has connection handles | Verify handles on all four sides (top, bottom, left, right) |

---

*This specification implements [ADR-049](../ADR-049-Canvas-Node-Enhancements.md).*
