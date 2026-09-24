# SPEC-253-A: Canvases Zoom Out to 5%

Implements **[ADR-253](../ADR-253-Canvas-Minimum-Zoom.md)**.

## 1. Changes

| File | Change |
|------|--------|
| `frontend/src/lib/canvas/zoom.ts` | New: `export const CANVAS_MIN_ZOOM = 0.05`. |
| `frontend/src/lib/canvas/UnifiedCanvas.svelte` | Both `<SvelteFlow>` instances (browse and edit) get `minZoom={CANVAS_MIN_ZOOM}`. |
| `frontend/src/lib/canvas/FullViewCanvas.svelte`, `ModelCanvas.svelte`, `BrowseCanvas.svelte` | `<SvelteFlow>` gets `minZoom={CANVAS_MIN_ZOOM}`. |

`fitView` (initial fit, the Controls fit button, and the `KeyboardHandler`
shortcut) uses the flow's `minZoom` when no override is passed, so no fitView
call site changes.

## 2. Tests (TDD)

- `frontend/tests/unit/canvasZoomRange.test.ts` (source contract, same style as
  `canvasTabFirst.test.ts`): `CANVAS_MIN_ZOOM` is > 0 and ≤ 0.05, and every
  `<SvelteFlow>` tag in the four canvases passes `minZoom={CANVAS_MIN_ZOOM}` and
  imports it from `$lib/canvas/zoom`. Red before the change (4 of 5 failed), green after.
- Full vitest suite: only the 7 failures that also fail on main.
- Manual browser check (Playwright, local dev): on a 19-node ArchiMate diagram,
  zoom-out goes from the fitted 0.78 down to 0.05 before the control disables
  itself (it stopped at 0.5 before).

## 3. Acceptance criteria

- Every Svelte Flow canvas can zoom out to 5%.
- Fit-to-view shows a large diagram whole instead of stopping at 50%.
- Maximum zoom and all other canvas behaviour are unchanged.
