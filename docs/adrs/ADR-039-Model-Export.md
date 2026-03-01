# ADR-039: Model Export

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-039 |
| **Initiative** | Export Model (WP-10) |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris modelling tool where users build architecture diagrams on an @xyflow/svelte canvas but have no way to share or archive their models outside the application,

**facing** the need for users to export diagrams for use in presentations, documentation, and offline reference in common formats (SVG, PNG, PDF), with future extensibility for interchange formats (Visio, Draw.io),

**we decided for** a client-side export approach that extracts the SVG content from the canvas DOM, converts it to SVG/PNG/PDF using browser-native APIs and the jsPDF library, and presents export options via a dropdown button in the canvas toolbar visible only in edit mode,

**and neglected** a server-side rendering approach using headless browser or cairosvg conversion (adds infrastructure complexity, latency, and server load for what is fundamentally a client-side rendering task), and a dedicated export page/dialog (over-engineers a simple download action),

**to achieve** fast, zero-latency diagram export that works entirely in the browser without additional backend endpoints, while maintaining a clean extension path for future interchange formats,

**accepting that** client-side SVG-to-PNG conversion via canvas may not perfectly reproduce all CSS styles (acceptable for architecture diagrams), and that jsPDF adds approximately 300KB to the frontend bundle (acceptable trade-off for PDF generation capability).

---

## Options Considered

### Option 1: Client-Side Export with jsPDF (Selected)

**Pros:**
- Zero backend changes required
- Instant export with no network round-trip
- jsPDF is a well-maintained library with broad browser support
- SVG export is lossless since it captures the actual rendered SVG
- PNG conversion uses native canvas API

**Cons:**
- CSS styles may not fully transfer to exported SVG/PNG
- jsPDF adds bundle size
- Complex diagrams may hit canvas size limits in some browsers

**Why selected:** Simplest approach that meets all current requirements. No server infrastructure needed.

### Option 2: Server-Side Rendering (Rejected)

**Pros:**
- Consistent output across browsers
- Can handle very large diagrams
- Could use cairosvg (already a project dependency for thumbnails)

**Cons:**
- Requires new API endpoints
- Adds server load for each export
- Introduces latency (network round-trip + server processing)
- Canvas state must be serialised and sent to server

**Why rejected:** Unnecessary complexity for a feature that works well client-side. The existing cairosvg dependency is for server-initiated thumbnail generation, not user-initiated exports.

### Option 3: Dedicated Export Dialog (Rejected)

**Pros:**
- Could offer more options (resolution, page size, margins)

**Cons:**
- Over-engineers a simple download action
- Adds UI complexity
- Delays the user's workflow

**Why rejected:** A simple dropdown is sufficient. Advanced options can be added later if needed.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-03-01 | Accepted | Implement client-side export | 6 months | 2026-09-01 |

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
| Depends On | ADR-030 | Model Canvas Toolbar Layout | Export dropdown integrates into the existing toolbar layout |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-039-A | Model Export Implementation | Technical Specification | [specs/SPEC-039-A-Model-Export.md](specs/SPEC-039-A-Model-Export.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
