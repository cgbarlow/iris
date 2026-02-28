# ADR-022: Server-Generated PNG Thumbnails

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-022 |
| **Initiative** | Server-Generated PNG Thumbnails for Gallery Cards |
| **Proposed By** | Architecture Team |
| **Date** | 2026-02-28 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris models gallery view (ADR-012, ADR-013), where gallery card thumbnails are currently rendered as inline SVG elements computed client-side from model `data` fields on every page load, resulting in rendering overhead at scale and no ability to serve thumbnails independently of the frontend,

**facing** the need for higher-fidelity PNG thumbnails that can be cached, served via API endpoints, and toggled by administrators between the existing SVG mode and a new server-generated PNG mode — and the existing `gallery_thumbnail_mode` admin setting (ADR-021) already anticipating this capability,

**we decided for** a server-side thumbnail generation pipeline that:

1. **Generates SVG** from model data (nodes/edges for canvas models, participants/lifelines for sequence models) on the backend using pure Python string construction.
2. **Converts SVG to PNG** using `cairosvg` when available, with graceful fallback to storing raw SVG bytes if `cairosvg` is not installed.
3. **Stores thumbnails** in a `model_thumbnails` table (model_id, BLOB, updated_at) with foreign key to models.
4. **Serves thumbnails** via `GET /api/models/{model_id}/thumbnail` with content-type detection (PNG magic bytes vs SVG) and cache headers.
5. **Regenerates thumbnails** automatically on model create and update operations.
6. **Frontend toggle** reads the `gallery_thumbnail_mode` admin setting and conditionally renders `<img>` tags pointing to the API endpoint (PNG mode) or the existing `ModelThumbnail.svelte` component (SVG mode).

**and neglected** client-side canvas-to-PNG conversion via `html2canvas` or `dom-to-image` (requires browser rendering context, cannot run server-side, poor cross-browser consistency), headless browser screenshot services (heavyweight infrastructure dependency for a thumbnail feature), and pre-rendering all thumbnails as static files on disk (no database-backed lifecycle management, complicates deployment),

**to achieve** a configurable thumbnail system where administrators can choose between lightweight client-side SVG rendering and higher-fidelity server-generated PNG thumbnails, with thumbnails served as cacheable API responses and automatically kept in sync with model changes,

**accepting that** `cairosvg` may not be available in all deployment environments (the system gracefully falls back to SVG bytes), the `model_thumbnails` table adds storage proportional to the number of models, and thumbnail regeneration adds a small overhead to model create/update operations.

---

## Options Considered

### Option 1: Server-Side SVG-to-PNG with Database Storage (Selected)

**Pros:**
- Thumbnails are pre-generated and cached in the database
- API endpoint enables independent serving with HTTP cache headers
- Graceful fallback when cairosvg is unavailable
- Admin toggle leverages existing settings infrastructure (ADR-021)
- Automatic regeneration on model changes keeps thumbnails current

**Cons:**
- Database storage grows with model count (approximately 15-30 KB per thumbnail)
- cairosvg dependency requires system-level Cairo libraries
- Thumbnail generation adds latency to create/update operations

**Why selected:** Best balance of fidelity, cacheability, and operational simplicity.

### Option 2: Client-Side Canvas-to-PNG (Rejected)

**Pros:**
- No backend changes needed
- Browser handles all rendering

**Cons:**
- Requires DOM rendering context (cannot pre-generate)
- Inconsistent results across browsers
- Cannot serve thumbnails via API

**Why rejected:** Incompatible with server-side serving and caching requirements.

### Option 3: Headless Browser Screenshots (Rejected)

**Pros:**
- Pixel-perfect screenshots of actual rendered canvases

**Cons:**
- Heavyweight dependency (Puppeteer/Playwright on backend)
- Significant infrastructure and resource overhead
- Slow generation time

**Why rejected:** Disproportionate infrastructure cost for thumbnail generation.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-28 | Accepted | Implement server-generated PNG thumbnails | 6 months | 2026-08-28 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Architecture Team | 2026-02-28 |
| Accepted | Project Lead | 2026-02-28 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Depends On | ADR-012 | Models Page Gallery View | Thumbnails displayed in gallery cards |
| Depends On | ADR-013 | Model Preview Thumbnails | Extends SVG thumbnails with PNG alternative |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-022-A | PNG Thumbnails | Technical Specification | [specs/SPEC-022-A-PNG-Thumbnails.md](specs/SPEC-022-A-PNG-Thumbnails.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
