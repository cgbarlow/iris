# SPEC-229-A: Mobile-responsive adaptation

Implements **[ADR-229](../ADR-229-Mobile-Responsive-Adaptation.md)**.

Living spec — evolves across the phased rollout. Phase 0 (foundations) is
implemented; later phases are specified here and filled in as they ship.

## Breakpoints

Mirror Tailwind v4 defaults:

| Band | Range | `viewport` flag |
|------|-------|-----------------|
| Mobile | `< 768px` | `isMobile` |
| Tablet | `768–1023px` | `isTablet` |
| Desktop | `≥ 1024px` | `isDesktop` |

Exactly one flag is true at any time. Desktop `≥ 1024px` matches the
pre-existing dashboard `matchMedia('(min-width: 1024px)')` boundary, so the
dashboard can migrate onto the store with no behaviour change.

## Mechanism rule

- **Tailwind responsive classes** (`md:`, `lg:`) for pure CSS layout —
  stacking columns, visibility, padding, gaps. No JS, SSR-safe, no flash.
- **The `viewport` JS store** only when a component *prop or behaviour* must
  change reactively: SvelteFlow `nodesDraggable`/`nodesConnectable`,
  drawer-vs-inline nav, bottom-sheet-vs-fixed panels, body scroll-lock.

## Phase 0 — Foundations (implemented)

### Viewport store

`frontend/src/lib/stores/viewport.svelte.ts` (new):

```ts
const MOBILE_MAX = 767;  // < 768px  → mobile
const DESKTOP_MIN = 1024; // ≥ 1024px → desktop; 768–1023px is tablet

// SSR/prerender default: render the desktop tree, reconcile on mount.
let isMobileState = $state(false);
let isDesktopState = $state(true);

// Call once from the root layout $effect; returns the matchMedia cleanup.
// No-ops + returns undefined when window.matchMedia is unavailable.
export function initViewport(): (() => void) | undefined { /* … */ }

export const viewport = {
  get isMobile()  { return isMobileState; },
  get isTablet()  { return !isMobileState && !isDesktopState; },
  get isDesktop() { return isDesktopState; },
};
```

Wired in `frontend/src/routes/+layout.svelte` via `$effect(() => initViewport())`.

Consume anywhere: `import { viewport } from '$lib/stores/viewport.svelte';`
then `{#if viewport.isMobile}…{/if}` (reactive through the getters).

### CSS tokens — `frontend/src/app.css`

- `--page-pad`: `1.5rem` desktop, `1rem` at `≤ 767px` (pages opt in).
- `.drawer-backdrop`: fixed full-bleed dim layer (`z-index: 45`) behind a
  drawer / bottom sheet.
- `body.scroll-locked { overflow: hidden }`: background scroll-lock while a
  drawer / sheet is open.

Existing WCAG utilities (24px touch targets, focus-visible, reduced-motion,
320px reflow) are reused, not duplicated. The mobile "use desktop to edit
layout" hint reuses `.canvas-mode-badge`.

### Test surface

- Playwright `mobile` project in `frontend/playwright.config.ts`:
  `{ ...devices['Pixel 5'] }`, `testMatch: /\.mobile\.spec\.ts$/`, same
  `localhost:4173` webServer. The `e2e` project gains
  `testIgnore: '**/*.mobile.spec.ts'` so the suites are disjoint. Run via
  `npm run test:mobile`.
- Unit: `frontend/tests/unit/viewport.test.ts` — boundary assertions at
  767/768/1023/1024, SSR default (matchMedia absent → desktop, no-op,
  cleanup undefined), reactivity on resize, listener cleanup.

## Phase 1 — App shell + nav drawer

`frontend/src/lib/components/AppShell.svelte`. Extract the nav list into a
`{#snippet}`. Desktop: existing inline `<nav class="w-56 …">` unchanged.
Mobile/tablet: render the same snippet inside a bits-ui `Dialog` left drawer
(`fixed left-0 top-0 h-full w-72` + `.drawer-backdrop`). Default closed on
mobile; hamburger toggles; auto-close on `afterNavigate` and on crossing to
desktop. Toggle `body.scroll-locked` via `$effect`. Header links wrap/shrink;
sign-out username `hidden sm:inline`.

Tests: `nav-drawer.mobile.spec.ts` — open/close via hamburger, Escape,
backdrop, nav-link; scroll-lock applied; focus returns to hamburger on close.

## Phase 2 — Lists + detail pages

`collections/+page.svelte`, `sets/+page.svelte`, `elements/+page.svelte`,
`elements/[id]/+page.svelte`, `packages/[id]/+page.svelte`. Page padding
`p-4 md:p-6`; toolbars `flex flex-wrap gap-2 md:gap-4`; tab bars wrapped in
`overflow-x-auto`; detail accordion grids `auto 1fr` → single column on mobile
(move inline `style=` to a class + `@media (max-width:767px)`); inputs
`w-full`; tables wrapped in `overflow-x-auto`. Reuse bits-ui `Accordion`.

Tests: `detail-stack.mobile.spec.ts`, `no-overflow.mobile.spec.ts`.

## Phase 3 — Diagram viewer

`frontend/src/routes/views/[id]/+page.svelte` + `UnifiedCanvas.svelte`. Gate
each of the three structural copies with `viewport.isMobile`. Hierarchy aside
→ bits-ui drawer; right panels → bottom sheets (drop the `margin-right:316px`
shift on mobile). Add `interactiveLayout = true` prop to `UnifiedCanvas`
`Props`; edit branch becomes `nodesDraggable={interactiveLayout}` /
`nodesConnectable={interactiveLayout && !connectMode}`; page passes
`interactiveLayout={!viewport.isMobile}`. Pan/pinch-zoom stay enabled. Show
the `.canvas-mode-badge` "Use desktop to edit layout" hint; hide
layout-authoring toolbar buttons on mobile (keep rename/property/comment).
Hide the FocusView trigger on mobile.

Tests: `canvas-readonly.mobile.spec.ts` — node drag leaves position unchanged,
connect handles inert, pane pan changes the transform, hint visible.

## Phase 4 — Iris AI chat

`frontend/src/routes/ask/+page.svelte`. Root height `100dvh` minus header so
the mobile URL bar / keyboard don't clip the composer. Config grid `1fr 1fr
1fr` → `grid-cols-1 md:grid-cols-3`; drop the `max-width:800px` cap on mobile
(`w-full md:max-w-[800px]`). Diagrams dropdown `min-width: min(320px,
calc(100vw - 32px))`. Composer full-width, sticky bottom; message list scrolls.

## Release

Each phase: feature branch → PR → `CHANGELOG.md` entry → version bump in
lockstep (frontend/package.json, backend/mcp/iris-client pyproject.toml; CLI
independent) → GitHub release. Phase 0 ships as v6.41.0.
