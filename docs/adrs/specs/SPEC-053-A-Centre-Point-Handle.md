# SPEC-053-A: Centre-Point Handle Implementation

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-053-A |
| **ADR** | [ADR-053](../ADR-053-Centre-Point-Connection-Mode.md) |
| **Status** | Approved |
| **Date** | 2026-03-01 |

---

## Overview

Add a centre-point connection handle to every canvas node component (Simple View, UML, ArchiMate) that enables straight centre-to-centre connections between nodes.

## Implementation

### Centre Handle Markup

Every node component receives an additional `Handle` element:

```svelte
<Handle type="source" position={Position.Top} id="center"
  class="center-handle"
  style="left:50%;top:50%;transform:translate(-50%,-50%);" />
```

- `type="source"` — since ConnectionMode.Loose is already configured, source-to-source connections work
- `position={Position.Top}` — required prop; actual position is overridden by inline style
- `id="center"` — unique handle identifier
- `class="center-handle"` — for CSS targeting

### CSS Styles (app.css)

```css
.svelte-flow .svelte-flow__handle.center-handle {
  opacity: 0;
  width: 16px;
  height: 16px;
  pointer-events: all;
}

.svelte-flow .svelte-flow__node:hover .svelte-flow__handle.center-handle {
  opacity: 0.6;
  background: var(--color-primary);
}
```

### Affected Components

**Simple View (8):**
- ActorNode, ComponentNode, DatabaseNode, InterfaceNode, ModelRefNode, PackageNode, QueueNode, ServiceNode

**UML (6):**
- ActivityNode, ClassNode, DeploymentNode, ObjectNode, StateNode, UseCaseNode

**ArchiMate (1):**
- ArchimateNode

### Test Coverage

- `centreHandle.test.ts` — Vitest unit test verifying all 15 node component files contain the centre handle markup

## Acceptance Criteria

1. All 15 node components contain a Handle with id="center"
2. Centre handle is invisible by default (opacity: 0)
3. Centre handle becomes visible on node hover
4. Users can drag from centre handle to create connections
5. Existing cardinal handles (top/bottom/left/right) remain unchanged
