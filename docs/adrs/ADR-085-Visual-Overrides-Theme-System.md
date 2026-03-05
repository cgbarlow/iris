# ADR-085: Per-Element Visual Overrides and Theme System

## Status
Accepted

## Context
Iris imports Sparx EA (.qea) files but discards all visual styling — colours, fonts, border styles, and explicit element dimensions. Every imported element renders with hardcoded notation defaults (white background, black borders for UML). The AIXM 5.1.1 model uses EA's default stereotype-based colour scheme, so faithful reproduction requires:

1. **Per-element visual overrides** — inline style data stored in `data.visual` on canvas nodes/edges
2. **A theme system** — maps stereotypes and element types to colours, linked to notation
3. **Explicit dimension support** — EA-computed width/height applied to rendered nodes instead of CSS auto-sizing

### Key findings
- All 882 AIXM diagram objects use `BCol=-1`, `Color=-1` (EA defaults) — zero custom colours
- Colours come entirely from EA's default UML palette + stereotype definitions
- The import reads EA coordinates correctly but stores dimensions in `measured`, which is only used for edge routing, not rendering

## Decision
Implement a three-layer visual system:

### 1. NodeVisualOverrides / EdgeVisualOverrides (Phase 1)
New interfaces on `CanvasNodeData` and `CanvasEdgeData` carrying optional inline style properties (bgColor, borderColor, fontColor, width, height, etc.). Applied as inline styles on renderer root elements.

### 2. EA Import Colour Preservation (Phase 2)
Extend the EA reader to extract ObjectStyle, Backcolor, Fontcolor, Bordercolor from t_object and t_diagramobjects. The converter builds visual override dicts and includes explicit EA dimensions in `data.visual.width/height`.

### 3. Theme System (Phases 3-4)
A `themes` table stores named theme configurations per notation. Each theme defines:
- `element_defaults` — per entity type colours
- `stereotype_overrides` — per stereotype colour overrides
- `edge_defaults` — per relationship type colours
- `global` — fallback defaults

**Style cascade** (most specific wins):
1. Per-element `data.visual`
2. Stereotype override from active theme
3. Element type default from active theme
4. Global default from active theme
5. Renderer hardcoded defaults

### 4. Per-Element Style Editor (Phase 5)
NodeStylePanel component with colour pickers and bold/italic toggles. Admin themes page for CRUD.

## Consequences
- Imported EA diagrams render with correct colours and dimensions
- Users can create new diagrams with EA-like styling via theme selection
- The theme system is general-purpose, usable for any notation
- Visual overrides persist in the existing `data` JSON column — no schema migration needed for node/edge data
- One new migration (m024_themes) for the themes table
