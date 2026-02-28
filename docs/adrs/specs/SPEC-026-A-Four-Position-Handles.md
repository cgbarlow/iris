# SPEC-026-A: Four-Position Handles Implementation

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-026-A |
| **ADR Reference** | [ADR-026: Canvas Four-Position Connection Handles](../ADR-026-Canvas-Four-Position-Handles.md) |
| **Date** | 2026-02-28 |
| **Status** | Active |

---

## Overview

This specification defines the implementation of four-position connection handles on all canvas node components. Each node gains left and right handles in addition to the existing top and bottom handles, and the SvelteFlow configuration is updated to use `connectionMode="loose"` for flexible edge attachment.

---

## Current Behaviour

All 14 canvas node components render exactly two `<Handle>` components:

```svelte
<Handle type="target" position={Position.Top} />
<Handle type="source" position={Position.Bottom} />
```

Edges can only connect to the top (incoming) or bottom (outgoing) of a node. Horizontal connections are not possible.

---

## New Behaviour

All 14 canvas node components render four `<Handle>` components with unique `id` attributes:

```svelte
<Handle type="target" position={Position.Top} id="top" />
<Handle type="source" position={Position.Bottom} id="bottom" />
<Handle type="target" position={Position.Left} id="left" />
<Handle type="source" position={Position.Right} id="right" />
```

- **Top** (`id="top"`): target handle, receives incoming edges from above
- **Bottom** (`id="bottom"`): source handle, sends outgoing edges downward
- **Left** (`id="left"`): target handle, receives incoming edges from the left
- **Right** (`id="right"`): source handle, sends outgoing edges to the right

Users can drag edges from any source handle (bottom, right) to any target handle (top, left) on another node.

---

## Affected Components

### Node Components (14 files)

#### Simple View Nodes
1. `frontend/src/lib/canvas/nodes/ActorNode.svelte`
2. `frontend/src/lib/canvas/nodes/ComponentNode.svelte`
3. `frontend/src/lib/canvas/nodes/DatabaseNode.svelte`
4. `frontend/src/lib/canvas/nodes/InterfaceNode.svelte`
5. `frontend/src/lib/canvas/nodes/PackageNode.svelte`
6. `frontend/src/lib/canvas/nodes/QueueNode.svelte`
7. `frontend/src/lib/canvas/nodes/ServiceNode.svelte`

#### UML Full View Nodes
8. `frontend/src/lib/canvas/uml/nodes/ActivityNode.svelte`
9. `frontend/src/lib/canvas/uml/nodes/ClassNode.svelte`
10. `frontend/src/lib/canvas/uml/nodes/DeploymentNode.svelte`
11. `frontend/src/lib/canvas/uml/nodes/ObjectNode.svelte`
12. `frontend/src/lib/canvas/uml/nodes/StateNode.svelte`
13. `frontend/src/lib/canvas/uml/nodes/UseCaseNode.svelte`

#### ArchiMate Full View Nodes
14. `frontend/src/lib/canvas/archimate/nodes/ArchimateNode.svelte`

### Canvas Configuration (2 files)

15. `frontend/src/lib/canvas/ModelCanvas.svelte` — add `connectionMode="loose"`
16. `frontend/src/lib/canvas/FullViewCanvas.svelte` — add `connectionMode="loose"`

---

## Implementation Details

### Handle Pattern

For each node component, the existing two handles are updated with `id` attributes and two new handles are added:

**Before:**
```svelte
<Handle type="target" position={Position.Top} />
<Handle type="source" position={Position.Bottom} />
```

**After:**
```svelte
<Handle type="target" position={Position.Top} id="top" />
<Handle type="source" position={Position.Bottom} id="bottom" />
<Handle type="target" position={Position.Left} id="left" />
<Handle type="source" position={Position.Right} id="right" />
```

No import changes are required — all components already import `Handle` and `Position` from `@xyflow/svelte`.

### SvelteFlow Configuration

The `connectionMode="loose"` prop is added to both `<SvelteFlow>` instances:

- `ModelCanvas.svelte`: Simple View canvas
- `FullViewCanvas.svelte`: Full View canvas (UML and ArchiMate)

This mode allows edges to connect between any source and target handles regardless of type, giving users maximum layout flexibility.

---

## Backward Compatibility

Existing edges stored without explicit `sourceHandle` and `targetHandle` fields will continue to work. The xyflow library falls back to default handle selection when handle IDs are not specified on an edge, connecting to the first available handle of the correct type.

---

## Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| 1 | All 14 node components render four Handle elements | Code review: each component has four `<Handle>` tags |
| 2 | Each handle has a unique `id` attribute (top, bottom, left, right) | Code review: `id` prop present on all handles |
| 3 | Top and left handles are type `target` | Code review: `type="target"` on top and left |
| 4 | Bottom and right handles are type `source` | Code review: `type="source"` on bottom and right |
| 5 | ModelCanvas uses `connectionMode="loose"` | Code review: prop present on `<SvelteFlow>` |
| 6 | FullViewCanvas uses `connectionMode="loose"` | Code review: prop present on `<SvelteFlow>` |
| 7 | Existing edges still render correctly | Manual verification: load a model with existing edges |

---

*This specification implements [ADR-026](../ADR-026-Canvas-Four-Position-Handles.md).*
