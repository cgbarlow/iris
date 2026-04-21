# ADR-126: Social Preview Card + Eye Favicon

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-126 |
| **Initiative** | Branding & Distribution |
| **Proposed By** | Engineering |
| **Date** | 2026-04-21 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** Iris v4.1.x shipping with anonymous read-only
access (ADR-123) and a public UAT deployment at
`iris-uat.chrisbarlow.nz` that is actively being shared in chat
platforms (LinkedIn, Slack, Teams, WhatsApp) — while `src/app.html`
ships only a charset + viewport meta, and `+layout.svelte` renders
only a favicon link, so pasted links appear as bare URLs with no
preview card; additionally the `favicon.svg` file that ships is still
the default Svelte-kit logo (an orange circle unrelated to Iris),

**facing** the user request to make pasted URLs render as a preview
card with an image, a meaningful title, and a short description across
every major chat platform; and to replace the placeholder favicon with
an eye design that reflects the Iris (goddess of the rainbow, and
more relevantly the anatomical eye) naming,

**we decided for** (a) a single global set of Open Graph + Twitter
Card meta tags rendered in the root `+layout.svelte` via
`<svelte:head>` — so every route inherits them at build time under
`adapter-static`, and per-page `<title>` tags already present
continue to override the default title without the OG tags needing
per-page overrides; (b) a copy of the user's dashboard screenshot
(`temp/iris.png`, 1258×902 PNG, 117 KB) moved to
`frontend/static/iris-preview.png` — no resizing or recompression,
the aspect ratio is close enough to the 1.91:1 Open Graph ideal that
every target platform renders the card correctly; (c) a deployment
env var `VITE_PUBLIC_URL` for resolving absolute URLs in the meta
tags (e.g., `https://iris-uat.chrisbarlow.nz`) — declared in
`render.yaml` with `sync: false` so it's set per-environment; (d) a
hand-written eye SVG (almond shape + blue iris + dark pupil + white
catch-light) replacing the Svelte-logo favicon, at 64×64 viewBox, no
external dependency,

**and neglected** (a) per-page OG tags (each route overrides its own
title + image) — the single global card is sufficient for v4.2 and
can be extended per-page later if a specific page needs its own; (b)
a dedicated 1200×630 composed marketing image (branded background +
text overlay) — the user explicitly asked to use their dashboard
screenshot, which has the benefit of showing real product surface;
(c) adding `apple-touch-icon` and other size variants — the single
SVG favicon works on every modern browser and iOS treats SVG
favicons correctly as of 2023+; (d) hardcoding the UAT URL into
`+layout.svelte` — using an env var means the same build works for
local dev (`""` fallback → relative `/iris-preview.png`), UAT, and
future prod without code edits; (e) PNG favicon fallback — the
single SVG is universally supported in browsers that matter; (f) a
ToolBar brand-mark change in `AppShell.svelte` — the header still
says "Iris" as text, which is fine and keeps the brand-mark change
scoped to the favicon alone,

**to achieve** a shareable, immediately-recognisable Iris link and a
tab icon that signals the product identity, shipped as a 30-line
change plus one static PNG plus a hand-written SVG — no new build
tooling, no image compositing pipeline, no per-page content overrides,

**accepting that** the preview card uses a single screenshot for every
page (a link to `/guide/ask-ai` renders the same card as a link to
`/`) — the trade-off for single-source simplicity; accepting that
`VITE_PUBLIC_URL` must be set in the Render dashboard for the
absolute URL to resolve correctly (when unset, the image renders with
a relative path that works on some platforms but not all — this is
documented in the deploy guide); accepting that the eye favicon is a
hand-drawn approximation not a commissioned icon — sufficient for the
current scope, easily replaced later by dropping a new SVG into the
same path; accepting that the chosen description copy (≤ 200 chars)
will need maintenance if Iris's positioning changes — the cost of
editing one string in `+layout.svelte` is trivial.

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| Social Preview Card | `<meta property="og:*">` + `<meta name="twitter:*">` tags in root `+layout.svelte`. Image `frontend/static/iris-preview.png` (user's dashboard screenshot). Absolute URL via `VITE_PUBLIC_URL` env var (declared in `render.yaml`, `sync: false`). Title `Iris — Integrated Repository for Information & Systems`. Description < 200 chars summarising the product. | _inline — no separate SPEC needed_ |
| Eye Favicon | Hand-written SVG at `frontend/src/lib/assets/favicon.svg` (replaces the default Svelte logo). 64×64 viewBox; almond eye shape + blue iris + dark pupil + white catch-light. Imported and linked in `+layout.svelte` (unchanged). | _inline_ |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Extends | ADR-122 | User Guide | User guide links will carry the same preview card when shared. |
| Coordinates | ADR-123 | Anonymous Read-Only Bypass | Anonymous visitors are the primary audience for shared links; the preview card works for them without authentication. |

---

## References

Inline decision. No SPEC required — the implementation surface is four
files (the image, the favicon SVG, `+layout.svelte`, `render.yaml`).

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-04-21 |
| Approved | Engineering | 2026-04-21 |
