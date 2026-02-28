# SPEC-013-A: Model Preview Thumbnails Implementation

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-013-A |
| **ADR Reference** | [ADR-013: Model Preview Thumbnails](../ADR-013-Model-Preview-Thumbnails.md) |
| **Date** | 2026-02-28 |
| **Status** | Active |

---

## Overview

This specification defines the implementation of static SVG preview thumbnails rendered from model `data` fields, displayed at the top of gallery cards on the models list page.

---

## Component: `ModelThumbnail.svelte`

**File:** `frontend/src/lib/components/ModelThumbnail.svelte`

### Props

| Prop | Type | Description |
|------|------|-------------|
| `data` | `Record<string, unknown>` | The model's `data` field containing nodes/edges or participants/messages |
| `modelType` | `string` | The model type (simple, component, sequence, uml, archimate) |

### Rendering Logic

The component renders an `<svg>` element with `data-testid="model-thumbnail"` and uses the model type to determine the rendering strategy.

#### Canvas Models (simple, component, uml, archimate)

These model types store diagram data as `data.nodes` (array of node objects with `position.x`, `position.y`) and `data.edges` (array of edge objects with `source`, `target` node IDs).

Rendering:
1. Parse `data.nodes` array — extract `id`, `position.x`, `position.y` for each node
2. Calculate bounding box from all node positions
3. Add padding (10% of each dimension, minimum 20px)
4. Set SVG `viewBox` to fit the bounding box with padding
5. Render each node as a small filled rounded rect (`rx="3"`) using `var(--color-primary)` fill
6. For each edge, find source and target node positions and render a line using `var(--color-border)` stroke

#### Sequence Models (sequence)

These model types store diagram data as `data.participants` (array of participant objects) and `data.messages` (array of message objects).

Rendering:
1. Parse `data.participants` — render circles evenly spaced across the top of the SVG
2. Draw vertical lifelines from each participant circle downward
3. Parse `data.messages` — render horizontal arrows between participant lifelines
4. Use `var(--color-primary)` for participant circles, `var(--color-border)` for lifelines and arrows

#### Empty/Unknown Models

If `data` is empty, has no nodes/participants, or the model type is unrecognised:
- Render centred muted text: "No diagram"
- Use `var(--color-muted)` for text colour

---

## Integration: Gallery Card Layout

**File:** `frontend/src/routes/models/+page.svelte`

The `ModelThumbnail` component is added at the top of each gallery card `<a>` element, inside a fixed-height container.

### Card Structure (Updated)

1. **Thumbnail** — fixed height (`h-28` / 7rem), overflow hidden, bottom border separator
2. **Model name** — `font-medium`, primary colour
3. **Model type badge** — small rounded badge with surface background
4. **Description** — full text, muted colour, only shown if present
5. **Updated date** — `toLocaleDateString()` format, muted colour, pushed to bottom with `mt-auto`

The thumbnail container uses `overflow: hidden` to clip SVG content that might extend beyond the fixed height.

---

## Theme Compatibility

All SVG colours use CSS custom properties:

| Element | Property |
|---------|----------|
| Node rects | `var(--color-primary)` fill |
| Edge lines | `var(--color-border)` stroke |
| Participant circles | `var(--color-primary)` fill |
| Lifelines | `var(--color-border)` stroke |
| Message arrows | `var(--color-border)` stroke |
| "No diagram" text | `var(--color-muted)` fill |
| SVG background | `var(--color-surface)` |

Works across Light, Dark, and High Contrast themes without additional styling.

---

## Accessibility

| Requirement | Implementation |
|-------------|----------------|
| Decorative image | SVG has `aria-hidden="true"` (thumbnail is supplementary to card text) |
| No information loss | All card text content (name, type, description, date) remains — thumbnail adds visual context only |

---

## Acceptance Criteria

| # | Criterion | Gherkin Scenario |
|---|-----------|-----------------|
| 1 | Gallery cards display SVG preview thumbnails | Gallery cards show preview thumbnails |
| 2 | Canvas models render nodes and edges | (Covered by scenario — seeded model has nodes/edges) |
| 3 | Empty models show "No diagram" placeholder | (Covered by scenario — seeded model without data) |
| 4 | Thumbnails use theme colours | (Visual — verified by theme compatibility) |

---

*This specification implements [ADR-013](../ADR-013-Model-Preview-Thumbnails.md).*
