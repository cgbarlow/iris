# ADR-013: Model Preview Thumbnails

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-013 |
| **Initiative** | Model Preview Thumbnails in Gallery Cards |
| **Proposed By** | Architecture Team |
| **Date** | 2026-02-28 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris models gallery view (ADR-012), where gallery cards currently display only text content (model name, type badge, description, and updated date), making it difficult for users to visually distinguish models at a glance,

**facing** the need for users to quickly identify models by their diagram structure — especially as the model collection grows — and the availability of model `data` fields already returned by `GET /api/models` containing node/edge and participant/message structures,

**we decided for** rendering static SVG preview thumbnails directly from model `data` within a new `ModelThumbnail.svelte` component, using bounding-box calculation to fit node/edge diagrams into a fixed-height SVG viewBox, with distinct rendering paths for canvas models (nodes as rounded rects, edges as lines) and sequence models (participant circles, lifelines, message arrows),

**and neglected** live SvelteFlow mini-instances (heavyweight, require `<SvelteFlow>` context wrapper, poor performance at gallery scale), server-side canvas screenshots via headless browser (adds infrastructure complexity, latency, and a new backend dependency), and third-party thumbnail/preview libraries (unnecessary dependency for simple SVG generation),

**to achieve** a visual browsing experience where users can identify models by their diagram structure without opening each one, improving the gallery view's utility for managing large collections of architectural models,

**accepting that** thumbnails are static approximations (not pixel-perfect canvas replicas), empty models show a "No diagram" placeholder, and the component reads from the existing `data` field without requiring API changes.

---

## Options Considered

### Option 1: Static SVG Thumbnails from Model Data (Selected)

**Pros:**
- No new dependencies — uses native SVG elements
- Lightweight — no canvas rendering engine needed
- Works with existing API response (no backend changes)
- Theme-compatible via CSS custom properties

**Cons:**
- Approximate visual representation, not pixel-perfect
- Must handle multiple model type formats (canvas vs sequence)

### Option 2: Live SvelteFlow Mini-Instances (Rejected)

**Pros:**
- Pixel-perfect representation of actual canvas

**Cons:**
- SvelteFlow requires `<SvelteFlow>` context — each card would need its own instance
- Heavy performance cost at gallery scale (dozens of flow instances)
- Complex lifecycle management for miniaturised canvases

**Why rejected:** The context requirement and performance cost make this impractical for a gallery of potentially many cards.

### Option 3: Server-Side Canvas Screenshots (Rejected)

**Pros:**
- Could produce high-fidelity raster thumbnails

**Cons:**
- Requires headless browser on the backend (Puppeteer/Playwright)
- Adds significant infrastructure complexity
- Introduces latency for thumbnail generation
- Thumbnails must be regenerated on every model change

**Why rejected:** Disproportionate infrastructure cost for a preview feature.

### Option 4: Third-Party Thumbnail Library (Rejected)

**Pros:**
- Potentially richer rendering options

**Cons:**
- Adds a dependency for simple SVG generation
- Increases bundle size
- May not support the specific data formats used by Iris

**Why rejected:** Native SVG elements are sufficient for the approximation needed.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-28 | Accepted | Implement static SVG thumbnails | 6 months | 2026-08-28 |

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
| Depends On | ADR-002 | Frontend Tech Stack | Uses Svelte 5 runes and native SVG |
| Depends On | ADR-012 | Models Page Gallery View | Thumbnails are rendered within gallery cards |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-013-A | Model Preview Thumbnails Implementation | Technical Specification | [specs/SPEC-013-A-Model-Preview-Thumbnails.md](specs/SPEC-013-A-Model-Preview-Thumbnails.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
