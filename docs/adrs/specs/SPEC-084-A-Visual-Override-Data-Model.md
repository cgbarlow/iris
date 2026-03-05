# SPEC-084-A: Visual Override Data Model

## Parent ADR
ADR-084: Per-Element Visual Overrides and Theme System

## Summary
Defines the `NodeVisualOverrides` and `EdgeVisualOverrides` interfaces stored in `CanvasNodeData.visual` and `CanvasEdgeData.visual`. These drive inline CSS styles on rendered nodes and edges.

## Interfaces

### NodeVisualOverrides
| Field | Type | Description |
|-------|------|-------------|
| bgColor | string? | CSS background colour |
| borderColor | string? | CSS border colour |
| fontColor | string? | CSS text colour |
| borderWidth | number? | Border width in px |
| fontSize | number? | Font size in px |
| bold | boolean? | Bold text |
| italic | boolean? | Italic text |
| width | number? | Explicit width in px (overrides CSS min-width) |
| height | number? | Explicit height in px (overrides CSS min-height) |

### EdgeVisualOverrides
| Field | Type | Description |
|-------|------|-------------|
| lineColor | string? | SVG stroke colour |
| lineWidth | number? | SVG stroke width |
| dashArray | string? | SVG stroke-dasharray |

## Helper Functions
- `nodeOverrideStyle(visual?)` — returns inline CSS string
- `edgeOverrideStyle(visual?)` — returns inline SVG style string

## Files
- `frontend/src/lib/types/canvas.ts` — interface definitions
- `frontend/src/lib/canvas/utils/visualStyles.ts` — helper functions
