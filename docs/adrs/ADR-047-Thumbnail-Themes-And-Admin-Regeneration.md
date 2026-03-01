# ADR-047: Thumbnail Themes & Admin Regeneration

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-047 |
| **Initiative** | Thumbnail Themes & Admin Regeneration (WP-1, WP-9) |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** server-generated PNG thumbnails (ADR-022) that currently render with a single fixed colour scheme, while Iris supports light, dark, and high-contrast themes, and administrators have no way to regenerate thumbnails after schema or rendering changes without restarting the server,

**facing** the need for theme-aware thumbnails that match the user's active theme and an administrative action to bulk-regenerate all thumbnails on demand,

**we decided for** (WP-1) a `THEME_COLORS` dictionary defining background, node fill, stroke, and text colours for `light`, `dark`, and `high-contrast` themes, parameterised SVG generation that injects theme colours before rasterisation, a composite primary key migration on the thumbnails table (`model_id`, `theme`), and a `?theme=` query parameter on the thumbnail GET endpoint that defaults to `light`; (WP-9) a `POST /api/admin/thumbnails/regenerate` endpoint guarded by the admin role that iterates all models and regenerates thumbnails for all themes, exposed via a "Regenerate Thumbnails" button on the admin settings page,

**and neglected** client-side theme application via CSS filters on a single thumbnail (produces poor colour fidelity and cannot accurately match theme palettes), storing per-theme thumbnails as separate files on disk rather than in the database (adds filesystem management complexity), and making regeneration automatic on every model save (unnecessary compute cost when thumbnails are only visually stale after rendering logic changes),

**to achieve** theme-consistent thumbnail previews throughout the gallery and model cards that respect the user's chosen theme, plus an admin escape hatch to refresh all thumbnails when the rendering pipeline changes,

**accepting that** the composite PK migration triples thumbnail storage (one row per model per theme), the regeneration endpoint may be slow for large model counts (acceptable as an infrequent admin action), and adding new themes in the future requires extending the `THEME_COLORS` dictionary and running regeneration.

---

## Options Considered

### Option 1: Server-Side Theme-Parameterised SVG + Admin Endpoint (Selected)

**Pros:**
- Pixel-perfect theme fidelity in thumbnails
- Reuses existing SVG rendering pipeline with minimal changes
- Admin regeneration decoupled from normal save flow
- `?theme=` query param is a clean, cacheable API design

**Cons:**
- Triples storage for three themes
- Composite PK migration required

**Why selected:** Delivers accurate theme rendering with a clean API contract and minimal frontend changes.

### Option 2: CSS Filters on Single Thumbnail (Rejected)

**Pros:**
- No additional storage; single thumbnail per model
- No backend changes needed

**Cons:**
- CSS `invert()`/`hue-rotate()` produces inaccurate colours
- Cannot match specific theme palettes (e.g., high-contrast yellow-on-black)
- Breaks down with multi-coloured node types

**Why rejected:** Insufficient colour fidelity for a professional UI.

### Option 3: Automatic Regeneration on Every Model Save (Rejected)

**Pros:**
- Thumbnails always up-to-date

**Cons:**
- Unnecessary compute on every save when rendering logic has not changed
- Increases save latency
- Generates thumbnails for themes the user may never view

**Why rejected:** Wasteful; rendering logic changes are infrequent and better handled by an explicit admin action.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-03-01 | Accepted | Add theme-aware thumbnails and admin regeneration | 6 months | 2026-09-01 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Architecture Team | 2026-03-01 |
| Accepted | Project Lead | 2026-03-01 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Depends On | ADR-022 | Server-Generated PNG Thumbnails | Extends existing thumbnail generation with theme support |
| Depends On | ADR-021 | Admin Settings and Configurable Session Timeout | Admin settings page hosts the regeneration button |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
