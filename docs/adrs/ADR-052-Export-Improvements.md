# ADR-052: Export Improvements

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-052 |
| **Initiative** | Export Improvements (WP-12) |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris model export functionality (ADR-039) where the current export captures only an incomplete view of the canvas and is restricted to edit mode, preventing browse-mode users from exporting diagrams,

**facing** the need for a full viewport capture that includes all rendered nodes and edges (not just the visible portion), and for the export action to be available in both edit and browse modes,

**we decided for** adopting the `html-to-image` library to perform a full viewport capture of the @xyflow/svelte canvas container (including all nodes, edges, labels, and handles), replacing the previous partial-capture approach, and making the export button always visible in the canvas toolbar regardless of the current mode (edit or browse),

**and neglected** server-side rendering of the canvas to PNG (would require replicating the entire @xyflow/svelte rendering pipeline on the backend), using the browser's native `window.print()` with CSS print styles (poor control over output dimensions and no PNG format), and canvas-based rendering via `html2canvas` (known issues with SVG foreignObject and @xyflow/svelte's overlay layers),

**to achieve** high-fidelity PNG export of the complete model diagram including all visual elements, available to all users in any mode, producing an image that matches exactly what is displayed on screen,

**accepting that** `html-to-image` adds a runtime dependency (~15KB gzipped), the export captures the current viewport styling including any browser-specific rendering differences, very large canvases may produce large images that take several seconds to generate, and the export is client-side only (no server involvement).

---

## Options Considered

### Option 1: html-to-image Full Viewport Capture (Selected)

**Pros:**
- Captures the complete DOM-rendered canvas including HTML overlay elements (labels, handles)
- Handles both SVG edges and HTML nodes correctly
- Lightweight library with no heavy dependencies
- Client-side only; no server infrastructure needed
- Produces pixel-accurate output matching the on-screen rendering

**Cons:**
- Adds a new runtime dependency
- Large canvases produce large images
- Cross-browser rendering differences may affect output

**Why selected:** Best fidelity-to-complexity ratio; captures exactly what the user sees with minimal integration effort.

### Option 2: Server-Side Canvas Rendering (Rejected)

**Pros:**
- Consistent output regardless of browser
- Could generate PDF or SVG in addition to PNG

**Cons:**
- Requires replicating @xyflow/svelte's rendering on the server (Puppeteer/Playwright headless)
- Significant infrastructure and maintenance cost
- Latency for server round-trip

**Why rejected:** Disproportionate complexity for a feature that works well client-side.

### Option 3: html2canvas Library (Rejected)

**Pros:**
- Well-known library with large community

**Cons:**
- Known issues with SVG `foreignObject` rendering
- Struggles with @xyflow/svelte's layered DOM structure (SVG + HTML overlays)
- Larger bundle size than `html-to-image`

**Why rejected:** Rendering fidelity issues with @xyflow/svelte's mixed SVG/HTML architecture.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-03-01 | Accepted | Adopt html-to-image for full viewport export | 6 months | 2026-09-01 |

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
| Depends On | ADR-039 | Model Export | Replaces the previous export mechanism with full viewport capture |
| Depends On | ADR-030 | Model Canvas Toolbar Layout | Export button placement in the toolbar |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
