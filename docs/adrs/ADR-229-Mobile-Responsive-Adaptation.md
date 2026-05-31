# ADR-229: Mobile-responsive adaptation (detect small screens, adapt the existing UI)

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-229 |
| **Initiative** | Make Iris usable on a phone — view everything, make light edits |
| **Proposed By** | Engineering |
| **Date** | 2026-05-31 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris frontend being desktop-first — the only
responsive code is a single inline `matchMedia('(min-width: 1024px)')`
on the dashboard (`frontend/src/routes/+page.svelte:231-238`); the app
shell carries a fixed 224px sidebar that overlaps content rather than
collapsing (`frontend/src/lib/components/AppShell.svelte`), the diagram
viewer renders a three-pane layout (280px hierarchy aside + canvas +
316px fixed right panels with a `margin-right:316px` page shift) in
`frontend/src/routes/views/[id]/+page.svelte`, and the detail / list /
AI-chat pages assume desktop width,

**facing** that a user on a phone gets a sidebar consuming ~40% of the
viewport, a canvas squeezed to an unusable width, right-side panels that
clip content, and horizontal overflow on several pages — while the
backend, MCP, and CLI surfaces are all reachable from mobile clients and
the actual blocker is purely the web UI's layout,

**we decided to** detect a mobile screen and **adapt the existing
components responsively in one codebase** (no separate mobile route
tree), targeting **view + light-edit** capability on mobile:

  - **Breakpoints** mirror Tailwind v4 defaults: `< 768px` = mobile,
    `768–1023px` = tablet, `≥ 1024px` = desktop (the existing dashboard
    boundary). A new reactive store
    `frontend/src/lib/stores/viewport.svelte.ts` generalises the inline
    matchMedia pattern into shared `isMobile / isTablet / isDesktop`
    getters, wired once from the root layout's `$effect`. SSR-safe:
    defaults to desktop when there is no `window` (adapter-static
    prerender), reconciles on mount.
  - **Mechanism rule** — use Tailwind responsive classes (`md:`, `lg:`)
    for pure CSS layout (stacking, visibility, padding); use the JS
    `viewport` store only when a component *prop or behaviour* must
    change reactively (canvas drag flags, drawer-vs-inline nav,
    bottom-sheet panels, body scroll-lock).
  - **App shell + nav** — the hamburger (already present) opens the nav
    as an overlay **drawer** on mobile (bits-ui `Dialog`, already a
    dependency), persistent inline on desktop (unchanged).
  - **Diagram canvas** stays pan / pinch-zoom **viewable** on mobile but
    layout authoring (node drag, edge draw) is disabled — a new
    `interactiveLayout` prop on `UnifiedCanvas.svelte` gates the existing
    edit-branch `nodesDraggable` / `nodesConnectable` flags, reusing the
    component's existing `browseMode` semantics rather than a parallel
    path. A "use desktop to edit layout" hint reuses `.canvas-mode-badge`.
    Light edits (rename, properties/text fields, comments) remain
    available.
  - **Lists / detail / AI chat** stack to single column, tab bars scroll
    horizontally, panels become bottom sheets on mobile.

  Delivered as **one ADR + one spec** (this ADR / SPEC-229-A) then a
  **phased rollout** — Phase 0 foundations (store, CSS tokens, Playwright
  mobile project, ADR/spec), Phase 1 app shell, Phase 2 lists/detail,
  Phase 3 diagram viewer, Phase 4 AI chat — each its own feature branch /
  PR / changelog entry / version bump.

**to achieve** a phone-usable Iris where every surface can be browsed and
lightly edited, without forking the UI into a parallel mobile codebase or
regressing the desktop experience.

**accepting** that:
- Heavy canvas authoring (drag-layout, drawing edges) is intentionally
  desktop-only on mobile. Touch-gesture authoring is out of scope (would
  reopen as a future ADR if demanded).
- The SSR default renders the desktop tree for one frame before
  `initViewport()` reconciles on a real phone — an acceptable, brief flash
  for the common (desktop) case, and avoids a mobile-tree flash for the
  majority.
- Tablets (768–1023px) get the mobile adaptations for now; a dedicated
  tablet layout is not in this initiative.
- The diagram viewer page is large (~3000 lines) with three structural
  copies (windowed / inline / FocusView); we gate each branch with the
  store rather than rewriting, accepting some conditional duplication.

## Rejected alternatives

- **Separate `/m` mobile route tree / dedicated mobile components** —
  maximum control over mobile UX but duplicates layout logic and doubles
  maintenance for every future feature. Responsive adaptation keeps one
  source of truth.
- **CSS-only (no JS store)** — can't express prop-level behaviour changes
  (disabling SvelteFlow node drag, swapping inline nav for a focus-trapped
  drawer). A small reactive store is the minimum needed; everything else
  stays CSS.
- **Hand-rolled drawer / bottom sheet** — bits-ui `Dialog` (already a
  dependency, Accordion already in use) gives focus trap, scroll-lock,
  Escape, `aria-modal`, and focus restoration for free. Don't reinvent.
- **Full mobile parity including touch canvas authoring** — large effort
  reworking xyflow interaction; not justified for the view + light-edit
  target.

## Dependencies

- Pattern source: the dashboard's inline matchMedia
  (`frontend/src/routes/+page.svelte:231-238`) — generalised by the new
  store; the dashboard migrates onto it as a fast-follow (same 1024px
  boundary, zero behaviour change).
- bits-ui 2.16 `Dialog` for the nav drawer and mobile bottom sheets.
- `UnifiedCanvas.svelte` existing `browseMode` branch (already sets
  `nodesDraggable/Connectable=false`) — reused via the new
  `interactiveLayout` prop.
- Existing WCAG CSS in `app.css` (24px touch targets, focus-visible,
  reduced-motion, 320px reflow) — built on, not duplicated.

## Consequences

- Spec: SPEC-229-A.
- Frontend-only. No backend change, no DB migration, no MCP / CLI surface
  change (Protocol §14 unaffected). Version numbers still bump in lockstep
  (frontend/backend/mcp/iris-client) per project discipline.
- New `frontend/src/lib/stores/viewport.svelte.ts` becomes the
  authoritative responsive-breakpoint primitive for the frontend.
- New Playwright `mobile` project (Pixel 5) and `*.mobile.spec.ts`
  convention establish the mobile test surface.
