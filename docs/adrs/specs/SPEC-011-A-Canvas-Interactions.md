# SPEC-011-A: Canvas Interactions

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-011-A |
| **ADR Reference** | [ADR-011: Canvas Integration and Testing Strategy](../ADR-011-Canvas-Integration-Testing.md) |
| **Date** | 2026-02-28 |
| **Status** | Active |

---

## Overview

This specification defines the complete interaction flows for the Simple View canvas in Iris, covering entity creation, relationship wiring, browse mode, keyboard operations, and persistence.

---

## End-to-End Flow: Simple View Canvas

1. User creates a model (via ModelDialog, type: simple or component)
2. User opens the model canvas (`/models/{id}`)
3. User adds an entity via EntityDialog (selects type from simpleViewNodeTypes)
4. Entity appears as a node on the canvas at the drop position
5. User connects two nodes by dragging from source handle to target handle
6. RelationshipDialog opens with source and target context
7. User selects relationship type and optional label
8. Edge is created on the canvas with the selected type
9. User saves the canvas (Ctrl+S or save button)
10. `PUT /api/models/{id}` sends `{ nodes, edges }` in the `data` field
11. User reloads the page
12. Canvas restores nodes and edges from persisted data

---

## Node Type Mapping

The entity type key **must** match the `simpleViewNodeTypes` registry keys. The `type` field passed to Svelte Flow's `addNode` must be the entity's `entityType`, not a hardcoded string.

| Entity Type Key | Display Name | Registry |
|----------------|-------------|----------|
| `component` | Component | simpleViewNodeTypes |
| `service` | Service | simpleViewNodeTypes |
| `interface` | Interface | simpleViewNodeTypes |
| `package` | Package | simpleViewNodeTypes |
| `actor` | Actor | simpleViewNodeTypes |
| `database` | Database | simpleViewNodeTypes |
| `queue` | Queue | simpleViewNodeTypes |

**Bug fix:** Replace any hardcoded `'simpleEntity'` type with the actual `entityType` value from the entity record. The node type must resolve to a registered key in `simpleViewNodeTypes` or Svelte Flow will render a fallback/invisible node.

---

## Relationship Creation Flow

| Step | Action | System Response |
|------|--------|----------------|
| 1 | User drags from source node handle | Connection line follows cursor |
| 2 | User drops on target node handle | `onconnect` callback fires |
| 3 | System opens RelationshipDialog | Dialog shows source label, target label, type selector, optional label input |
| 4 | User selects relationship type | Type stored in dialog state |
| 5 | User optionally enters a label | Label stored in dialog state |
| 6 | User confirms | Edge added to canvas with `{ type, label, source, target }` |
| 7 | User cancels | No edge created, dialog closes |

Available simple view relationship types: `association`, `dependency`, `composition`, `aggregation`, `generalization`.

---

## Browse Mode

Browse mode provides read-only canvas exploration for stakeholders.

| Step | Action | System Response |
|------|--------|----------------|
| 1 | User navigates to browse route (`/models/{id}/browse`) | BrowseCanvas renders with nodes and edges (read-only) |
| 2 | User clicks a node | EntityDetailPanel opens showing entity data |
| 3 | EntityDetailPanel displays | Label, type, description, entityId |
| 4 | User clicks close button on panel | Panel closes, selection cleared |

Browse mode restrictions: no drag, no connect, no add, no delete.

---

## Keyboard Operations

| Key | Action | Context |
|-----|--------|---------|
| `Tab` | Cycle focus through canvas nodes | Canvas focused |
| Arrow keys | Move selected node(s) by grid increment | Node(s) selected |
| `C` | Open connection mode from focused node | Node focused |
| `Delete` | Delete selected node(s) and connected edges | Node(s) selected |
| `Ctrl+N` | Open EntityDialog to add new entity | Canvas focused |
| `Ctrl+=` | Zoom in | Canvas focused |
| `Ctrl+-` | Zoom out | Canvas focused |
| `Ctrl+0` | Reset zoom to fit view | Canvas focused |
| `F` | Fit view (zoom to show all nodes) | Canvas focused |
| `Escape` | Deselect all / close open dialog | Any |

---

## Persistence

### Save

- Trigger: `Ctrl+S` or save button
- Request: `PUT /api/models/{id}`
- Payload: `{ data: { nodes, edges } }`
- Nodes include: `id`, `type`, `position`, `data` (entity reference)
- Edges include: `id`, `type`, `source`, `target`, `label`

### Load

- On route mount, `GET /api/models/{id}` returns model with `data` field
- Parse `data.nodes` and `data.edges`
- Restore canvas state from parsed data

---

## Acceptance Criteria (Gherkin Scenario Mapping)

| Scenario | Gherkin Summary |
|----------|----------------|
| Add entity to canvas | Given an open model, When I add a component entity, Then a component node appears |
| Connect two entities | Given two nodes, When I connect them, Then RelationshipDialog opens and edge is created |
| Delete a node | Given a selected node, When I press Delete, Then the node and its edges are removed |
| Save and reload | Given a canvas with nodes and edges, When I save and reload, Then all nodes and edges are restored |
| Browse mode click | Given browse mode, When I click a node, Then EntityDetailPanel shows entity data |
| Keyboard navigation | Given a canvas with nodes, When I press Tab, Then focus cycles through nodes |
| simpleEntity bug fix | Given an entity with type 'service', When it renders, Then the node type is 'service' not 'simpleEntity' |

---

*This specification implements [ADR-011](../ADR-011-Canvas-Integration-Testing.md).*
