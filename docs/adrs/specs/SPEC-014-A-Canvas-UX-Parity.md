# SPEC-014-A: Canvas UX Parity Implementation

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-014-A |
| **ADR Reference** | [ADR-014: Canvas UX Parity](../ADR-014-Canvas-UX-Parity.md) |
| **Date** | 2026-02-28 |
| **Status** | Active |

---

## Overview

This specification covers three coordinated UX improvements: removing duplicate zoom controls from canvas models, adding zoom/pan/fit-to-view to sequence diagrams via SVG viewBox manipulation, adding sequence diagram edit mode, and introducing a focus view overlay for all model types.

---

## A. Remove Duplicate Zoom Controls

### Changes

Remove `<CanvasToolbar>` from:
- `ModelCanvas.svelte`: Remove import and `<CanvasToolbar onannounce={handleAnnounce} />`
- `FullViewCanvas.svelte`: Remove import and `<CanvasToolbar onannounce={handleAnnounce} />`

Delete `CanvasToolbar.svelte` from `src/lib/canvas/controls/`.

Remove `.canvas-toolbar` and `.canvas-toolbar__btn` CSS rules from `app.css`.

### Remaining Zoom Controls

- `<Controls showLock={false} />` — SvelteFlow built-in controls (bottom-left, all canvas types)
- `KeyboardHandler` — Keyboard shortcuts (Ctrl+=, Ctrl+-, Ctrl+0, F key)

---

## B. Sequence Diagram Zoom/Pan/Fit-to-View

### useSequenceViewport.svelte.ts (NEW)

Svelte 5 runes module providing viewport state and handlers:

- **State:** `zoom` (default 1), `panX`/`panY` (default 0)
- **Derived:** `viewBox` string computed as `"{panX} {panY} {contentWidth/zoom} {contentHeight/zoom}"`
- **Methods:**
  - `zoomIn()` — Increase zoom by 0.2 step, clamp to max 4x
  - `zoomOut()` — Decrease zoom by 0.2 step, clamp to min 0.25x
  - `fitView()` — Reset zoom to 1, panX/panY to 0
  - `handleWheel(e)` — Ctrl+wheel = zoom, plain wheel = vertical pan
  - `handlePointerDown/Move/Up(e)` — Middle-button or Shift+left-button drag = pan

### SequenceToolbar.svelte (NEW)

Callback-based zoom toolbar for sequence diagrams:

- **Props:** `onzoomin`, `onzoomout`, `onfitview`
- **Visual:** Reuses SvelteFlow control CSS classes (`svelte-flow__controls`, `svelte-flow__controls-button`) for consistent bottom-left positioning
- **Accessibility:** Same button labels and ARIA attributes as SvelteFlow Controls

### SequenceDiagram.svelte (MODIFY)

- Remove explicit `width` and `height` attributes from `<svg>`
- Add optional `viewBox` prop; default to `"0 0 {diagramWidth} {diagramHeight}"`
- Add `preserveAspectRatio="xMidYMid meet"`
- Wire `onwheel`, `onpointerdown`, `onpointermove`, `onpointerup` event props

### Model Detail Page Integration

- Sequence container: change from `overflow: auto; padding: 1rem; min-height: 300px` to `height: 500px; overflow: hidden`
- Instantiate `createSequenceViewport(diagramWidth, diagramHeight)`
- Wire `viewBox` prop and toolbar callbacks to SequenceDiagram and SequenceToolbar

---

## C. Sequence Diagram Edit Mode

### ParticipantDialog.svelte (NEW)

Follows `EntityDialog.svelte` pattern:
- `<dialog>` with `showModal()`, DOMPurify sanitisation, Escape handler
- Fields: Name (text, required), Type (select: actor/component/service)
- Props: `open`, `onsave(name, type)`, `oncancel`

### MessageDialog.svelte (NEW)

Follows `EntityDialog.svelte` pattern:
- Fields: From (select from participants), To (select from participants), Label (text, required), Type (select: sync/async/reply)
- Props: `open`, `participants`, `onsave(from, to, label, type)`, `oncancel`

### Model Detail Page — Sequence Edit/Browse

Replace sequence branch with edit/browse toggle matching canvas pattern:

- **Browse mode:** "Edit Canvas" button, read-only SequenceDiagram + SequenceToolbar
- **Edit mode:** "Add Participant", "Add Message", "Delete Selected", "Save", "Discard" toolbar
- **Empty state:** "No participants yet" + "Start Building" button (matching canvas empty state)
- **Save:** `PUT /api/models/{id}` with `data: { participants, messages, activations }`

---

## D. Focus View

### FocusView.svelte (NEW)

- `position: fixed; inset: 0; z-index: 50; background: var(--color-bg)`
- Children slot fills 100% width/height
- "Exit Focus" button (top-right corner, x icon)
- Escape key to exit
- `role="dialog"`, `aria-label="Focus view"`
- Props: `onexit: () => void`

### Model Detail Page Integration

- `let focusMode = $state(false)`
- "Focus" button in toolbar row (all model types)
- When active: wrap canvas container in `<FocusView>`, container height changes from `500px` to `100%`
- Escape exits focus mode
- Focus mode persists across edit/browse switch

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| No duplicate zoom controls on canvas models | Open canvas model; verify only bottom-left SvelteFlow Controls visible, no top-right buttons |
| Sequence diagram fits within container | Create sequence model with participants; verify SVG fits within 500px container |
| Sequence diagram has zoom controls | Open sequence model; verify zoom in/out/fit buttons visible at bottom-left |
| Sequence diagram zoom/pan works | Use Ctrl+wheel to zoom, Shift+drag to pan; verify viewBox updates |
| Sequence diagram edit mode | Enter edit mode; add participant and message; save and reload; verify data persists |
| Focus view expands canvas | Click Focus button; verify fullscreen overlay; press Escape to exit |
| Focus view works for all model types | Test focus view on simple, UML, ArchiMate, and sequence models |
| Keyboard shortcuts unaffected | Verify Ctrl+=/-/0 still work on canvas models |

---

*This specification implements [ADR-014](../ADR-014-Canvas-UX-Parity.md).*
