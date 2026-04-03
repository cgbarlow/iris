# SPEC-117-B: Graph Settings Frontend

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-117-B |
| **ADR** | [ADR-117](../ADR-117-Graph-Settings-Admin-Defaults.md) |
| **Status** | Approved |
| **Date** | 2026-04-03 |

## Overview

Extends the `GraphSettings` type with four numeric physics/display fields, adds slider controls and action buttons to the settings panel, implements a three-layer settings cascade (hard-coded, admin DB defaults, user localStorage), and wires the new parameters into the force graph physics.

## Frontend

### Extended type (`frontend/src/lib/types/api.ts`)

```typescript
export interface GraphSettings {
    nodes: Record<string, boolean>;
    edges: Record<string, boolean>;
    label_density: number;   // 1–50, default 10
    node_spacing: number;    // 0.2–3.0, default 1.0
    size_contrast: number;   // 0.0–1.0, default 1.0
    link_length: number;     // 0.2–3.0, default 1.0
}
```

The four new fields are always present on `GraphSettings`. The hard-coded defaults object in the dashboard page initialises them:

```typescript
const GRAPH_SETTINGS_DEFAULTS: GraphSettings = {
    nodes: { collection: true, set: true, package: true, diagram: true, element: true },
    edges: {
        collection_membership: true, set_membership: true, direct_diagram_links: true,
        hierarchy: true, package_relationship: true, diagram_element: true,
        diagram_package: true, diagram_link: true, element_relationship: true,
    },
    label_density: 10,
    node_spacing: 1.0,
    size_contrast: 1.0,
    link_length: 1.0,
};
```

### Settings cascade

The dashboard page (`frontend/src/routes/+page.svelte`) resolves settings on mount in three layers:

1. **Hard-coded defaults** — the `GRAPH_SETTINGS_DEFAULTS` constant above.
2. **Admin DB defaults** — fetched via `GET /api/graph/settings?scope_type=set&scope_id=<id>` (or `collection`/`global` as appropriate). The backend returns a fully-merged object, so the frontend applies it as a single overlay on top of hard-coded defaults.
3. **User localStorage** — read from `localStorage.getItem('graph-settings-<scope_type>-<scope_id>')`. Parsed as JSON and merged key-by-key on top of the DB defaults.

Merge logic (shallow per top-level key, deep for `nodes`/`edges`):

```typescript
function mergeSettings(base: GraphSettings, overlay: Partial<GraphSettings>): GraphSettings {
    return {
        ...base,
        ...overlay,
        nodes: { ...base.nodes, ...(overlay.nodes ?? {}) },
        edges: { ...base.edges, ...(overlay.edges ?? {}) },
    };
}
```

On every settings change from the panel, the merged result is written back to localStorage.

### Settings panel UI (`frontend/src/lib/components/KnowledgeGraphSettings.svelte`)

The existing node-type checkboxes and edge-group checkboxes remain unchanged. Below them, add a new section:

#### Physics / Display controls

| Control | HTML Element | Bound field | Min | Max | Step | Display |
|---------|-------------|-------------|-----|-----|------|---------|
| Label density | `<input type="number">` | `label_density` | 1 | 50 | 1 | Integer, no units |
| Node spacing | `<input type="range">` | `node_spacing` | 0.2 | 3.0 | 0.1 | Value shown as `{value}x` |
| Size contrast | `<input type="range">` | `size_contrast` | 0.0 | 1.0 | 0.05 | Value shown as percentage `{Math.round(value * 100)}%` |
| Link length | `<input type="range">` | `link_length` | 0.2 | 3.0 | 0.1 | Value shown as `{value}x` |

Layout: each control is a row with a text label on the left and the input on the right, consistent with the existing checkbox rows. A horizontal rule separates this section from the visibility toggles above.

#### Action buttons

Below the physics controls, two buttons separated by a horizontal rule:

| Button | Label | Visibility | Behaviour |
|--------|-------|------------|-----------|
| Save as default | "Save as default" | Admin users only | Calls `PUT /api/graph/settings` with the current settings for the active scope. Shows a brief "Saved" confirmation. |
| Reset to defaults | "Reset to defaults" | All users | Clears the localStorage entry for the current scope and re-fetches DB defaults via GET, effectively reverting to admin defaults (or hard-coded if none set). |

Admin detection: the dashboard page passes an `isAdmin` prop to the settings panel, derived from the auth store's `current_user.role === 'admin'`.

### KnowledgeGraph.svelte physics integration

The four new settings fields are applied as multipliers to the existing force configuration.

#### Node spacing (`node_spacing`)

Applied to the charge force strength. Each per-type charge value is multiplied by `settings.node_spacing`:

```typescript
chargeForce.strength((n: any) => {
    const base =
        n.node_type === 'collection' ? -300 :
        n.node_type === 'set' ? -200 :
        n.node_type === 'package' ? -80 :
        n.node_type === 'diagram' ? -40 : -30;
    return base * settings.node_spacing;
});
```

Higher `node_spacing` values push nodes further apart; lower values pack them tighter.

#### Link length (`link_length`)

Applied to the link force distance. Each per-edge-type distance value is multiplied by `settings.link_length`:

```typescript
linkForce.distance((l: any) => {
    const base =
        l.edge_type === 'collection_membership' ? 200 :
        l.edge_type === 'set_membership' ? (tgtType === 'package' ? 60 : tgtType === 'diagram' ? 120 : 80) :
        l.edge_type === 'hierarchy' ? (tgtType === 'package' ? 25 : 40) :
        (l.edge_type === 'diagram_element' || l.edge_type === 'diagram_package') ? 40 : 60;
    return base * settings.link_length;
});
```

#### Size contrast (`size_contrast`)

Applied to the `nodeVal` callback. Interpolates between a uniform size (`uniformSize`) and the full type-based size (`base`) using the contrast factor:

```typescript
const UNIFORM_SIZE = 8;

.nodeVal((n: any) => {
    const base =
        n.node_type === 'collection' ? 160 :
        n.node_type === 'set' ? 55 :
        n.node_type === 'package' ? 40 :
        n.node_type === 'diagram' ? 12 : 0.5;
    return UNIFORM_SIZE + (base - UNIFORM_SIZE) * settings.size_contrast;
})
```

**Formula:** `renderedSize = UNIFORM_SIZE + (typeSize - UNIFORM_SIZE) * size_contrast`

- At `size_contrast = 1.0`: full differentiation, values are `160`, `55`, `40`, `12`, `0.5` (current behaviour).
- At `size_contrast = 0.0`: all nodes render at `UNIFORM_SIZE` (8), giving a flat, equal-size layout.
- At `size_contrast = 0.5`: sizes are halved toward uniform — `84`, `31.5`, `24`, `10`, `4.25`.

#### Label density (`label_density`)

Applied in the `onRenderFramePost` callback. The existing `MAX_PER_TIER` constant (currently hard-coded to `10`) is replaced by `settings.label_density`:

```typescript
.slice(0, settings.label_density)
```

Higher values show more labels (denser text), lower values show fewer (cleaner layout).

### Reactivity

When any of the four physics fields change via the settings panel:

1. The `$effect` block that watches `filteredNodes`/`filteredEdges` already calls `updateGraph(graph)`.
2. `updateGraph` must re-apply `chargeForce.strength()`, `linkForce.distance()`, `nodeVal()`, and the label density. This requires moving the force configuration into `updateGraph` (or a dedicated `applyPhysics` helper) rather than only setting it once in `onMount`.
3. After applying new physics, call `graph.d3ReheatSimulation()` to restart the force simulation so nodes settle into the new layout.

### localStorage key format

```
graph-settings-global
graph-settings-collection-<uuid>
graph-settings-set-<uuid>
```

Only the four numeric fields and the `nodes`/`edges` visibility maps are stored. No auth tokens or sensitive data.

### Error handling

- If the `GET /api/graph/settings` call fails (network error, 500), fall back silently to hard-coded defaults merged with localStorage. Log a warning to console.
- If the `PUT /api/graph/settings` call fails, show an error toast and do not clear the user's pending changes.
