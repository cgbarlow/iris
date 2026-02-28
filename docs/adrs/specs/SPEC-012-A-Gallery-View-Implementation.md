# SPEC-012-A: Gallery View Implementation

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-012-A |
| **ADR Reference** | [ADR-012: Models Page Gallery View](../ADR-012-Models-Gallery-View.md) |
| **Date** | 2026-02-28 |
| **Status** | Active |

---

## Overview

This specification defines the implementation of a gallery/card view mode for the models list page, including a view mode toggle, card resize slider, responsive CSS grid layout, and localStorage persistence.

---

## View Mode Toggle

Two toggle buttons in the toolbar (after the sort dropdown):

| Button | Icon | `aria-pressed` | Description |
|--------|------|----------------|-------------|
| List | `☰` | `true` when `viewMode === 'list'` | Default view — single-line items |
| Gallery | `▦` | `true` when `viewMode === 'gallery'` | Card grid view |

- Buttons use `aria-pressed` to communicate state to assistive technology
- Active button has a distinct visual style (primary colour background)
- Default view mode is `list`

---

## Card Size Slider

| Property | Value |
|----------|-------|
| Element | `<input type="range">` |
| `min` | `200` |
| `max` | `400` |
| `step` | `50` |
| `aria-label` | `Card size` |
| Default value | `250` |
| Visibility | Only visible when `viewMode === 'gallery'` |

The slider adjusts the `minmax()` first argument in the CSS grid template.

---

## Gallery Card Layout

### CSS Grid

```css
grid-template-columns: repeat(auto-fill, minmax({cardSize}px, 1fr))
gap: 1rem (16px)
```

### Card Content

Each card is an `<a>` linking to `/models/{id}` and displays:

1. **Model name** — `font-medium`, primary colour
2. **Model type badge** — small rounded badge with surface background
3. **Description** — full text (not truncated), muted colour, only shown if present
4. **Updated date** — `toLocaleDateString()` format, muted colour, pushed to bottom with `mt-auto`

### Card Styling

- Rounded border matching theme (`--color-border`)
- Padding: `1rem`
- Flex column layout with `gap: 0.5rem`
- Hover effect: border colour changes to primary

---

## localStorage Persistence

| Key | Value | Default |
|-----|-------|---------|
| `iris-models-view` | `'list'` or `'gallery'` | `'list'` |
| `iris-models-card-size` | Number string (`'200'` to `'400'`) | `'250'` |

- Values are read on component mount (with SSR guard `typeof window !== 'undefined'`)
- Values are written on change via `$effect`
- Persistence survives page navigation and browser refresh

---

## Accessibility

| Requirement | Implementation |
|-------------|----------------|
| Toggle state | `aria-pressed` on toggle buttons |
| Slider label | `aria-label="Card size"` on range input |
| Keyboard | Toggle buttons and slider are natively keyboard-accessible |
| Focus visible | Uses existing focus indicator styles (2px, 3:1 contrast) |
| Screen reader | Toggle buttons announce pressed state; slider announces value |

---

## Theme Compatibility

The gallery view uses CSS custom properties for all colours:

- `--color-border` for card borders
- `--color-fg` for text
- `--color-primary` for model names and hover states
- `--color-surface` for type badge background
- `--color-muted` for descriptions and dates
- `--color-bg` for card background (via `--color-surface`)

Works across Light, Dark, and High Contrast themes without additional styling.

---

## Acceptance Criteria

| # | Criterion | Gherkin Scenario |
|---|-----------|-----------------|
| 1 | Default view is list mode | Default view is list mode |
| 2 | Toggle switches to gallery view | Switching to gallery view |
| 3 | Gallery cards show model name and type | Gallery cards show model details |
| 4 | Card size slider adjusts card width | Resizing cards with the slider |
| 5 | View preference persists across navigation | View preference persists across navigation |
| 6 | Slider is hidden in list view | Slider is hidden in list view |

---

*This specification implements [ADR-012](../ADR-012-Models-Gallery-View.md).*
