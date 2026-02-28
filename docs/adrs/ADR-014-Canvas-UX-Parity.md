# ADR-014: Canvas UX Parity

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-014 |
| **Initiative** | Sequence Diagram UX Parity, Focus View, and Zoom Control Cleanup |
| **Proposed By** | Architecture Team |
| **Date** | 2026-02-28 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris canvas system where sequence diagrams lack zoom/pan and fit-to-view capabilities (large diagrams overflow horizontally with `overflow: auto`), users have no fullscreen focus mode for any canvas type, and canvas models display duplicate zoom controls in both the top-right CanvasToolbar and bottom-left SvelteFlow Controls,

**facing** the need for UX parity across all model types — ensuring sequence diagrams offer the same navigation experience as SvelteFlow-based canvases — and the desire for a distraction-free focus mode that works across all canvas types,

**we decided for** three coordinated changes:

1. **Sequence zoom/pan:** SVG-native `viewBox` manipulation via a `useSequenceViewport` runes module, providing zoom (Ctrl+wheel), pan (middle-button/Shift+left drag, plain wheel), and fit-to-view (reset) without external dependencies.
2. **Focus view:** A CSS `position: fixed; inset: 0` overlay component (`FocusView.svelte`) with Escape to exit, available for all model types in both browse and edit modes.
3. **Zoom control deduplication:** Remove `CanvasToolbar.svelte` (top-right zoom buttons), retaining the SvelteFlow `<Controls>` component (bottom-left) and `KeyboardHandler` keyboard shortcuts (Ctrl+=/-/0) as the single source of zoom controls.

**and neglected** embedding sequence diagrams in SvelteFlow (incompatible with custom SVG renderer), CSS transform-based zoom (degrades SVG text rendering quality), third-party zoom/pan libraries (unnecessary dependency given SVG viewBox support), and the Fullscreen API for focus mode (permission prompts and inconsistent browser behaviour),

**to achieve** consistent zoom/pan/fit-to-view across all canvas types, a clean focus mode for deep work, and a single set of zoom controls that avoids user confusion from duplicate buttons,

**accepting that** SVG viewBox manipulation has slightly different interaction feel than SvelteFlow's built-in zoom, and the focus view uses a CSS overlay rather than true browser fullscreen.

---

## Options Considered

### Sequence Zoom/Pan

#### Option 1: SVG viewBox Manipulation (Selected)

**Pros:**
- Native SVG feature, no dependencies
- Smooth zoom with preserved text quality
- Simple state model (zoom, panX, panY)

**Cons:**
- Must implement wheel/pointer handlers manually

**Why selected:** SVG viewBox is the standard mechanism for viewport control in SVG documents. It preserves text rendering quality and requires minimal code.

#### Option 2: CSS Transforms (Rejected)

**Pros:**
- Works with any HTML/SVG content

**Cons:**
- Degrades SVG text rendering at non-1x scales
- Browser inconsistencies with transform-origin

**Why rejected:** Text quality degradation is unacceptable for diagram labels.

#### Option 3: Embed in SvelteFlow (Rejected)

**Pros:**
- Would reuse existing zoom infrastructure

**Cons:**
- SvelteFlow expects node/edge data model, incompatible with custom SVG renderer
- Would require rewriting the entire sequence renderer

**Why rejected:** Architectural incompatibility with the custom SVG-based sequence renderer.

### Focus View

#### Option 1: CSS Fixed Overlay (Selected)

**Pros:**
- No browser permissions needed
- Consistent across all browsers
- Simple implementation with Escape to exit

**Cons:**
- Not true fullscreen (browser chrome remains)

**Why selected:** Reliable cross-browser behaviour without permission prompts.

#### Option 2: Fullscreen API (Rejected)

**Pros:**
- True fullscreen, hides browser chrome

**Cons:**
- Requires user gesture and permission
- Inconsistent across browsers (especially Firefox/Safari)
- Complex error handling for denied permissions

**Why rejected:** Permission inconsistencies make it unreliable for a core UX feature.

### Zoom Control Deduplication

#### Option 1: Keep SvelteFlow Controls Only (Selected)

**Pros:**
- SvelteFlow Controls is the standard, well-positioned bottom-left control
- KeyboardHandler already covers keyboard shortcuts
- Eliminates confusing duplicate buttons

**Cons:**
- Loses the top-right positioning some users may prefer

**Why selected:** One canonical location for zoom controls reduces confusion. Keyboard shortcuts remain available everywhere.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-28 | Accepted | Implement all three changes | 6 months | 2026-08-28 |

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
| Depends On | ADR-011 | Canvas Integration and Testing Strategy | Extends canvas interaction patterns |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-014-A | Canvas UX Parity Implementation | Technical Specification | [specs/SPEC-014-A-Canvas-UX-Parity.md](specs/SPEC-014-A-Canvas-UX-Parity.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
