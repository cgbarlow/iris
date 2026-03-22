# SPEC-099-A: Linked Diagram Editor

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-099-A |
| **ADR** | [ADR-099](../ADR-099-Linked-Diagram-Property-Editor.md) |
| **Status** | Draft |
| **Date** | 2026-03-22 |

---

## Overview

Add a "Linked Diagram" panel to the edit sidebar that appears when a node is selected in edit mode. Allows setting, changing, or clearing the node's `linkedModelId`.

## Component

**`LinkedDiagramPanel.svelte`** — new component in `frontend/src/lib/canvas/controls/`

**Props:** `nodeId`, `linkedModelId`, `excludeDiagramId`

**Behaviour:**
- Fetches diagram name via `GET /api/diagrams/{linkedModelId}` when set
- Shows `"DiagramName" [Change] [×]` when linked
- Shows `[Link Diagram]` button when unlinked
- Handles deleted diagrams gracefully (404 → "Diagram not found")
- Uses existing `DiagramPicker` for diagram selection

**Event:** Dispatches `nodedatachange` CustomEvent with `{ nodeId, field: 'linkedModelId', value }` — reuses existing handler at `+page.svelte:358` which pushes undo history and sets dirty flag.

## Acceptance Criteria

1. Edit mode → select node → "Linked Diagram" section visible in sidebar
2. Click "Link Diagram" → DiagramPicker opens → select → name displayed
3. Click "Change" → pick different diagram → updates
4. Click × → clears link
5. Save → reload → link persists
6. Browse mode → click linked node → navigates to target diagram
7. Undo after linking → reverts the change
