# SPEC-116-B: Knowledge Graph Component

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-116-B |
| **ADR** | [ADR-116](../ADR-116-Knowledge-Graph-Visualization.md) |
| **Status** | Approved |
| **Date** | 2026-04-03 |

## Overview

A Svelte 5 wrapper around the `force-graph` library embedded on the dashboard page, rendering a force-directed knowledge graph of elements and relationships.

## Frontend

### Dependency

`force-graph` — Canvas-based 2D force-directed graph using d3-force.

### Types (`frontend/src/lib/types/api.ts`)

```typescript
export interface GraphNode {
    id: string;
    name: string;
    element_type: string;
    description: string | null;
    relationship_count: number;
    diagram_usage_count: number;
}

export interface GraphEdge {
    id: string;
    source: string;
    target: string;
    relationship_type: string;
    label: string | null;
}

export interface GraphResponse {
    nodes: GraphNode[];
    edges: GraphEdge[];
}
```

### Utility (`frontend/src/lib/utils/graphColors.ts`)

Deterministic colour palette mapping `element_type` strings to a fixed 10-colour palette. `getElementTypeColor(type, allTypes)` returns a hex colour string.

### Component (`frontend/src/lib/components/KnowledgeGraph.svelte`)

| Prop | Type | Description |
|------|------|-------------|
| `nodes` | `GraphNode[]` | Graph nodes |
| `edges` | `GraphEdge[]` | Graph edges |
| `onNodeClick` | `(nodeId: string) => void` | Click handler |

**Behaviour:**
- Imperative `ForceGraph` instance created in `onMount`, cleaned up on destroy
- Node colour by `element_type` via `graphColors.ts`
- Node size proportional to `relationship_count`
- Directional arrows on edges
- Edge labels from `label` or `relationship_type`
- Responsive via `ResizeObserver`
- Theme-aware: reads `--color-bg`, `--color-fg`, `--color-muted` CSS custom properties
- Theme change detected via `MutationObserver` on `<html>` class attribute
- Click navigates to `/elements/{id}`
- Hover shows tooltip with name + element_type

### Dashboard integration (`frontend/src/routes/+page.svelte`)

- Collapsible "Knowledge Graph" section below the search section
- Only renders when `setId` or `collectionId` is active
- Loads data via `apiFetch<GraphResponse>('/api/graph?set_id=...')`
- Shows empty state when no elements exist

## Dependencies Added

| Package | Version |
|---------|---------|
| `force-graph` | latest stable |
