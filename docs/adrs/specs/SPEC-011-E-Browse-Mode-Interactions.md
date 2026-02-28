# SPEC-011-E: Browse Mode Interactions

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-011-E |
| **ADR Reference** | [ADR-011: Canvas Integration and Testing Strategy](../ADR-011-Canvas-Integration-Testing.md) |
| **Date** | 2026-02-28 |
| **Status** | Active |

---

## Overview

This specification defines how EntityDetailPanel is wired into BrowseCanvas, the node click to panel display flow, panel content, close behaviour, and the stakeholder browsing experience. Browse mode is a read-only view of a model canvas intended for stakeholders who need to explore architecture diagrams without editing them.

---

## EntityDetailPanel Wiring in BrowseCanvas

EntityDetailPanel is an existing component that is currently built but not rendered in any route. This spec wires it into BrowseCanvas.

### Integration Point

BrowseCanvas registers an `onnodeclick` handler on the Svelte Flow instance. When a node is clicked, BrowseCanvas:

1. Reads the node's `data` property (which contains the entity reference)
2. Sets the `selectedEntity` state to the clicked node's entity data
3. Renders EntityDetailPanel with the selected entity

```svelte
<script>
    let selectedEntity = $state(null);

    function handleNodeClick(event) {
        const node = event.detail.node;
        selectedEntity = node.data.entity;
    }

    function handlePanelClose() {
        selectedEntity = null;
    }
</script>

<SvelteFlow
    {nodes}
    {edges}
    nodesDraggable={false}
    nodesConnectable={false}
    onnodeclick={handleNodeClick}
>
    <!-- canvas content -->
</SvelteFlow>

{#if selectedEntity}
    <EntityDetailPanel
        entity={selectedEntity}
        onclose={handlePanelClose}
    />
{/if}
```

---

## Node Click to Panel Display Flow

| Step | Actor | Action | System Response |
|------|-------|--------|----------------|
| 1 | Stakeholder | Clicks on a node in BrowseCanvas | `onnodeclick` fires |
| 2 | BrowseCanvas | Sets `selectedEntity` from node data | EntityDetailPanel renders |
| 3 | Stakeholder | Views entity information in panel | Panel displays label, type, description, entityId |
| 4 | Stakeholder | Clicks close button on panel | `onclose` callback fires |
| 5 | BrowseCanvas | Sets `selectedEntity` to null | Panel unmounts, selection cleared |
| 6 | Stakeholder | Clicks a different node | Previous panel closes, new panel opens with new entity |
| 7 | Stakeholder | Clicks canvas background (not a node) | No change (panel remains open if already open) |

---

## EntityDetailPanel Content

The panel renders the following fields from the entity data:

| Field | Source | Display |
|-------|--------|---------|
| **Label** | `entity.name` | Heading text at top of panel |
| **Type** | `entity.entity_type` | Badge or tag showing the entity type (e.g., "Service", "Component") |
| **Description** | `entity.description` | Body text, supports multi-line |
| **Entity ID** | `entity.id` | Monospace text, useful for cross-referencing |

### Panel Position

EntityDetailPanel renders as a side panel (right-aligned) overlaying the canvas. It does not displace canvas content. The panel width is fixed (320px) and scrollable if content overflows.

### Empty States

| Condition | Display |
|-----------|---------|
| `entity.description` is null or empty | Show "No description" in muted text |
| `entity.entity_type` is unknown | Show the raw type string as-is |

---

## Close Behaviour

The panel can be closed through the following interactions:

| Trigger | Behaviour |
|---------|-----------|
| Close button (X) in panel header | `onclose` fires, `selectedEntity` set to null |
| `Escape` key | `onclose` fires, `selectedEntity` set to null |
| Clicking a different node | Previous entity replaced with new entity (panel stays open) |

Clicking the canvas background does **not** close the panel. This is intentional -- stakeholders may pan the canvas while reviewing entity details.

---

## Stakeholder Browsing Flow

Browse mode is designed for stakeholders who are not editors. The complete flow:

1. Stakeholder receives a link to `/models/{id}/browse`
2. BrowseCanvas renders with all nodes and edges from the model
3. Canvas is fully read-only:
   - `nodesDraggable={false}` -- nodes cannot be moved
   - `nodesConnectable={false}` -- no connection handles shown
   - No EntityDialog or RelationshipDialog available
   - No delete operations available
   - No save button rendered
4. Stakeholder can pan (click-drag on background) and zoom (scroll wheel, pinch)
5. Stakeholder clicks a node to view its details in EntityDetailPanel
6. Stakeholder clicks close or a different node to navigate the diagram
7. Keyboard navigation: Tab cycles through nodes, Enter or Space opens EntityDetailPanel for the focused node

### Accessibility in Browse Mode

| Interaction | Keyboard | Screen Reader |
|------------|----------|---------------|
| Navigate between nodes | Tab / Shift+Tab | Node label announced on focus |
| Open entity detail | Enter or Space on focused node | "Entity detail panel opened" announced |
| Close entity detail | Escape | "Entity detail panel closed" announced |
| Zoom | Ctrl+= / Ctrl+- / Ctrl+0 | Zoom level announced |

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Node click opens EntityDetailPanel | Click a node in browse mode; verify panel appears with entity data |
| Panel shows label, type, description, entityId | Verify all four fields render correctly for a known entity |
| Close button clears panel | Click X; verify panel unmounts and selectedEntity is null |
| Escape closes panel | Press Escape; verify panel unmounts |
| Clicking different node switches panel | Click node A, then node B; verify panel shows node B data |
| No drag in browse mode | Attempt to drag a node; verify it does not move |
| No connect in browse mode | Verify no connection handles are visible |
| Tab cycles through nodes | Press Tab repeatedly; verify focus moves through nodes |
| Empty description shows fallback | Click a node with no description; verify "No description" text |

---

*This specification implements [ADR-011](../ADR-011-Canvas-Integration-Testing.md).*
