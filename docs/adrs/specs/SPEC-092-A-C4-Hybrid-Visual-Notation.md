# SPEC-092-A: C4 Hybrid Visual Notation + Canvas & UX Polish

**ADR:** ADR-092
**Date:** 2026-03-09

## Part A: C4 Visuals

### 1. C4 colour constants — `frontend/src/lib/canvas/utils/visualStyles.ts`

Add a `C4_COLOURS` map keyed by C4 element type:

```ts
export const C4_COLOURS = {
  Person:         { border: '#08427B', fill: 'rgba(8,66,123,0.10)',  text: '#08427B' },
  SoftwareSystem: { border: '#1168BD', fill: 'rgba(17,104,189,0.10)', text: '#1168BD' },
  Container:      { border: '#438DD5', fill: 'rgba(67,141,213,0.10)', text: '#438DD5' },
  Component:      { border: '#85BBF0', fill: 'rgba(133,187,240,0.10)', text: '#85BBF0' },
} as const;
```

### 2. Inline SVG shape glyphs — `frontend/src/lib/canvas/renderers/C4Renderer.svelte`

Replace Lucide icon rendering with inline SVG shape glyphs per C4 type:
- **Person:** 16×16 SVG with a head circle and shoulders arc.
- **Software System:** 16×16 rounded rectangle outline.
- **Container:** 16×16 hexagon outline.
- **Component:** 16×16 circle with inner dot.

Render the glyph in the node header, left of the element name. Use the `C4_COLOURS[type].border`
colour for the glyph stroke.

### 3. Tinted fill and border — `frontend/src/lib/canvas/renderers/C4Renderer.svelte`

Apply styling to the node wrapper:
- `border: 2px solid {C4_COLOURS[type].border}`
- `background: {C4_COLOURS[type].fill}`
- `border-radius: 8px`

### 4. Technology label — `frontend/src/lib/canvas/renderers/C4Renderer.svelte`

When `node.data.technology` is present, render it below the element name:

```svelte
{#if node.data.technology}
  <span class="c4-technology">[{node.data.technology}]</span>
{/if}
```

Style with `font-size: 0.75rem; color: var(--text-muted); margin-top: 2px;`.

## Part B: UX Polish

### 5. NotationPills component — `frontend/src/lib/canvas/controls/NotationPills.svelte` (new)

Create a horizontally scrollable pill bar component:
- **Props:** `items: Array<{ value: string; label: string; icon?: string }>`, `selected: string`,
  `onSelect: (value: string) => void`
- Each pill is a `<button>` with border-radius, the type icon (if any), and the label.
- Active pill gets a filled background; inactive pills are outlined.
- Container uses `overflow-x: auto; white-space: nowrap; scrollbar-width: thin`.

### 6. Replace dropdown with NotationPills — `frontend/src/lib/canvas/controls/NodeStylePanel.svelte`

Replace the `<select>` element for diagram-type / element-type selection with the `NotationPills`
component. Pass the available types from the notation registry as `items`.

### 7. Rename "Entity" to "Element" — multiple files

Search-and-replace user-facing strings:
- `frontend/src/routes/elements/[id]/+page.svelte` — page title, breadcrumb labels
- `frontend/src/lib/canvas/controls/NodeStylePanel.svelte` — panel heading, tooltips
- `frontend/src/lib/canvas/controls/KeyboardHandler.svelte` — shortcut descriptions
- `frontend/src/lib/canvas/sequence/SequenceToolbar.svelte` — toolbar labels

Only change user-facing labels and aria-labels, not code identifiers or API field names.

### 8. Theme loading skeleton — `frontend/src/routes/diagrams/[id]/+page.svelte`

Add an `isThemeLoaded` reactive flag. Until the theme fetch resolves, render a skeleton placeholder
(pulsing grey rectangles matching typical node positions) instead of the `<UnifiedCanvas>`.

```svelte
{#if isThemeLoaded}
  <UnifiedCanvas ... />
{:else}
  <div class="canvas-skeleton">
    <div class="skeleton-node" />
    <div class="skeleton-node" />
    <div class="skeleton-node" />
  </div>
{/if}
```

## Part C: Canvas Polish

### 9. Connection handle visibility — `frontend/src/lib/canvas/BaseNode.svelte`

Update handle styles to improve visibility on coloured backgrounds:
- Increase handle diameter from 6px to 10px.
- Add a 2px white border (`outline: 2px solid white; border: 2px solid var(--handle-color)`).
- On hover, scale to 14px with a transition.

### 10. Edge routing per notation — `frontend/src/lib/canvas/UnifiedCanvas.svelte`

Set default edge type based on diagram notation:
- C4 diagrams: `defaultEdgeOptions.type = 'default'` (bezier curves).
- UML / ArchiMate diagrams: keep `defaultEdgeOptions.type = 'smoothstep'`.

Read the notation from the diagram metadata and pass the appropriate default.

### 11. Edit mode badge — `frontend/src/lib/canvas/controls/KeyboardHandler.svelte`

When `editMode` is true, render a small badge in the toolbar area:

```svelte
{#if editMode}
  <span class="edit-mode-badge">Editing</span>
{/if}
```

Style: `background: var(--accent); color: white; padding: 2px 8px; border-radius: 4px;
font-size: 0.75rem; font-weight: 600;`.

## Part D: Version History UI

### 12. Rollback action — `frontend/src/routes/diagrams/[id]/+page.svelte`

Add a "Restore this version" button to each version history entry. On click:
1. Fetch the full diagram content for the selected version via `GET /api/diagrams/{id}/versions/{version}`.
2. POST it as a new version via `POST /api/diagrams/{id}/versions` with the restored content.
3. Reload the canvas with the new current version.

### 13. Version diff preview — `frontend/src/routes/diagrams/[id]/+page.svelte`

Before confirming rollback, show a summary dialog:
- Count of added, removed, and modified nodes.
- Count of added, removed, and modified edges.
- Compute by diffing node/edge ID sets and comparing serialised data for shared IDs.

### 14. Relative timestamps — `frontend/src/routes/diagrams/[id]/+page.svelte`

Format version timestamps with a relative time helper (e.g., "2 hours ago", "yesterday").
Show the absolute ISO timestamp in a `title` attribute for hover tooltip.

### 15. Backend version restore endpoint — `backend/app/diagrams/router.py`

Add `POST /api/diagrams/{id}/versions` that accepts a full diagram payload (nodes + edges +
metadata) and creates a new version entry. This reuses the existing version-creation logic but
sources content from the request body rather than the current canvas state.

## Test Plan

- Unit test: `C4_COLOURS` map contains all four C4 element types with valid hex colours.
- Unit test: C4Renderer renders inline SVG glyph matching the element type.
- Unit test: C4Renderer applies tinted fill and border from `C4_COLOURS`.
- Unit test: NotationPills renders pills for all provided items, highlights selected.
- Unit test: "Entity" string does not appear in user-facing labels (grep check).
- Unit test: theme skeleton renders when `isThemeLoaded` is false, canvas renders when true.
- Unit test: connection handles have white border outline in rendered markup.
- Unit test: edge type defaults to `default` for C4, `smoothstep` for UML.
- Unit test: edit mode badge visible when `editMode` is true, hidden when false.
- Integration test: version restore creates a new version with content matching the source version.
- Integration test: version diff summary correctly counts added/removed/modified nodes and edges.
