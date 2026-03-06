# Sparx EA Faithful Formatting — Gap Analysis Report

**Date:** 2026-03-05
**Branch:** `sparxea-faithful-formatting`
**Reference Diagram:** AIXM 5.1.1 "Diagram_Main" (class Main)
**Iris URL:** `/diagrams/3aa49022-e6f4-4668-9e97-3d306bb77b22`
**Ground Truth:** [AIXM HTML export](https://aixm.aero/sites/default/files/imce/AIXM511HTML/AIXM/Diagram_Main.html) / saved image `temp/download.gif`

---

## Executive Summary

Despite v2.2.0 adding EAP import support and v2.3.0 adding per-element visual overrides and themes, Iris still does **not** faithfully reproduce Sparx EA diagram rendering. The ground truth AIXM "Main" diagram shows 8 classes/objects with rich UML notation — attribute compartments with visibility markers, composition/dependency connectors with multiplicity labels, role names, arrowheads, and orthogonal routing. Iris imports most of the **data** correctly but fails to **render** it faithfully.

The gaps fall into three categories:
1. **Data imported but not rendered** (cardinality, roles, arrowheads)
2. **Data not threaded to canvas nodes** (attributes not on canvas)
3. **Rendering fidelity gaps** (routing, line paths, label placement)

---

## Detailed Gap Analysis: Ground Truth vs Iris

### What the EA Ground Truth Shows (AIXM Diagram_Main)

The reference diagram contains:

| Element | Type | Attributes Shown |
|---------|------|-----------------|
| AIXMFeature | Class (italic — abstract) | `+ identifier :CodeUUIDType` |
| AIXMMessage | Class | `+ sequenceNumber :NoSequenceType` |
| AIXMTimeSlice | Class | `+ correctionNumber :NoNumberType`, `+ interpretation :TimeSliceInterpretationType`, `+ sequenceNumber :NoNumberType`, `+ validTime :TimePrimitive` |
| ISO 19115 Metadata::MD_Metadata | Class | (none shown) |
| AIXMFeaturePropertyGroup | Class | `+ featureLifetime :TimePrimitive` |
| AIXMObject | Class | (none shown) |
| Extension | Class (italic — abstract) | (none shown) |
| Feature Properties | Note | Rich text body |

**Visual characteristics observed in EA:**
- Cream/tan background colour on all class boxes (`#f2e6c9` approximate)
- Red font colour for attribute text
- `+` visibility markers before attribute names (UML public visibility)
- Attribute format: `+ name :Type` (visibility, name, colon, type)
- Bold class names, italic for abstract classes
- Composition diamonds (filled black) on associations
- Dependency arrows (dashed lines with open arrowheads)
- Multiplicity labels at both ends of associations (e.g., `0..*`, `1`, `1..*`)
- Role names on association ends (e.g., `+timeSlice`, `+propertyGroup`, `+extension`, `+complexProperty`)
- Orthogonal (right-angle) line routing on all connectors
- Note element with dog-ear corner and rich text body
- Frame label "class Main" in top-left corner
- Connector label positions close to endpoints, not centred

---

## Gap 1: Attributes Not Rendered on Canvas Nodes (CRITICAL)

**Severity: High — this is the single most visible difference**

### What happens now
- Attributes ARE imported from `t_attribute` and stored in `element_data["attributes"]` as rich objects with `name`, `type`, `scope`, etc.
- But attributes are **NOT threaded through to canvas node data**.
- The `UmlRenderer.svelte` component DOES support attribute compartments (lines 73-86), reading from `data.attributes`.
- However, the import service (`service.py:473-497`) builds `node_data` with `label`, `entityType`, `entityId`, `description`, `stereotype`, and `visual` — but **never copies `attributes`** from the element data to the canvas node data.

### What it should look like
Each class node should show a compartment below the class name with attributes formatted as:
```
+ identifier :CodeUUIDType
+ correctionNumber :NoNumberType
```

### What's needed
1. During import, copy element `data.attributes` into `node_data.attributes` on the canvas node
2. Format attributes with UML visibility markers: `+` (public), `-` (private), `#` (protected), `~` (package) — sourced from `Scope` field in `QeaAttribute`
3. The `UmlRenderer` already renders `{attr.name}: {attr.type}` — it needs to prepend the visibility marker

---

## Gap 2: No Arrowheads / UML Markers on Edges (CRITICAL)

**Severity: High — connectors are visually ambiguous without markers**

### What happens now
- All UML edge components (`CompositionEdge.svelte`, `GeneralizationEdge.svelte`, `DependencyEdge.svelte`, etc.) accept a `markerEnd` prop and pass it through to Svelte Flow's `BaseEdge`.
- **But nothing in the system ever SETS `markerEnd`**. No SVG `<marker>` definitions exist in the canvas (only in `DiagramThumbnail.svelte` for the thumbnail preview).
- Result: all edges render as plain lines with no visual distinction between composition, generalization, dependency, etc. except dash pattern.

### What EA shows
| Relationship Type | EA Rendering |
|---|---|
| Composition | Solid line + filled black diamond at source |
| Aggregation | Solid line + open diamond at source |
| Generalization | Solid line + closed white triangle at target |
| Dependency | Dashed line + open arrowhead at target |
| Realization | Dashed line + closed white triangle at target |
| Association | Solid line + optional open arrow for navigability |

### What's needed
1. Define SVG `<defs>` with `<marker>` elements for each UML arrowhead type (filled diamond, open diamond, closed triangle, open arrow)
2. Set `markerEnd` (and `markerStart` for diamonds) on edges based on relationship type
3. This is the infrastructure that makes composition vs dependency vs generalization visually distinguishable

---

## Gap 3: Cardinality Labels Not Rendered (HIGH)

**Severity: High — multiplicity is core UML information**

### What happens now
- Cardinality data IS imported: `sourceCardinality` and `targetCardinality` are stored in both relationship `data` and canvas edge `data`.
- The `ViewConfig` in `viewStore.svelte.ts` has `show_cardinality: true` flag.
- **But no edge rendering component reads or renders cardinality.** The flag is defined but never consumed by any canvas component.
- Result: `0..*`, `1`, `1..*` labels that appear at connector endpoints in EA are completely invisible in Iris.

### What EA shows
- Small text labels positioned near the source and target ends of each connector
- e.g., `0..*` near AIXMTimeSlice end of the timeSlice association, `1..*` near the other end

### What's needed
1. Render `sourceCardinality` as a text label near the source end of the edge path
2. Render `targetCardinality` as a text label near the target end
3. Position labels offset from the endpoint (typically ~15-20px along the path, offset perpendicular)

---

## Gap 4: Role Names Not Rendered (HIGH)

**Severity: High — role names are essential context in the EA diagram**

### What happens now
- Role names ARE imported: `sourceRole` and `targetRole` stored in edge data.
- `show_role_names: true` flag exists in ViewConfig but is never consumed.
- Result: `+timeSlice`, `+propertyGroup`, `+extension`, `+complexProperty` labels completely invisible.

### What's needed
1. Render role names near each endpoint, alongside (but distinct from) cardinality labels
2. In EA, role names typically appear on the opposite side of the line from cardinality

---

## Gap 5: Edge Routing — Bezier vs Orthogonal (MEDIUM)

**Severity: Medium — changes the visual shape of the diagram significantly**

### What happens now
- The import captures `RouteStyle` and maps `3` to `"step"` (orthogonal) and `0` to `"bezier"`.
- The AIXM data has `RouteStyle=3` (orthogonal) on virtually all connectors.
- The `BaseEdge.svelte` component handles `routingType: "step"` via `getSmoothStepPath({ borderRadius: 0 })`.
- **But Svelte Flow's `getSmoothStepPath` only creates simple L-shaped or Z-shaped paths between two points.** It does NOT reproduce EA's complex multi-segment orthogonal routing with intermediate waypoints.

### What EA shows
- Right-angle connector paths that may have 3-5 segments, routing around other elements
- Waypoints stored in `t_diagramlinks.Geometry` field — which Iris does NOT read

### What's needed
1. Read `t_diagramlinks` table to get per-diagram connector geometry/waypoints
2. Parse the `Geometry` field (EA's proprietary format encoding path segments)
3. Use custom edge path rendering with intermediate waypoints instead of Svelte Flow's built-in algorithms
4. This is the most complex gap to close — marked as "stretch goal" in existing analysis

---

## Gap 6: Diagram Frame / Title Block (LOW)

**Severity: Low — cosmetic framing**

### What happens now
- No diagram frame or title block rendered. EA shows "class Main" in a tab in the top-left corner with a full border rectangle around the diagram.

### What's needed
- Optional diagram frame border with notation + name label in top-left tab

---

## Gap 7: Note Element Styling (LOW)

**Severity: Low — notes render but styling differs**

### What happens now
- Notes render with yellow background and dog-ear corner (via `NoteNode.svelte`).
- HTML content is rendered via `{@html}` with DOMPurify sanitisation.
- The visual is reasonable but uses a different shade of yellow and slightly different proportions than EA.

### What EA shows
- Off-white/cream note background with folded corner
- Rich text body with bold and underline formatting

### What's needed
- Minor CSS adjustments to match EA's note styling more closely
- Low priority

---

## Gap 8: Attribute Visibility Markers and Font Styling (MEDIUM)

**Severity: Medium — the `+` markers and red font are signature EA visual cues**

### What happens now
- Attribute `Scope` is imported (Public, Private, Protected, Package).
- `UmlRenderer` renders attributes as `{name}: {type}` — no visibility prefix.
- No per-attribute font colour support. EA shows attribute text in red/dark red.

### What EA shows
- `+ identifier :CodeUUIDType` (plus sign = public)
- Red-coloured attribute text (distinct from black class name)

### What's needed
1. Map `Scope` to UML visibility: Public→`+`, Private→`-`, Protected→`#`, Package→`~`
2. Prepend visibility marker to attribute rendering
3. Consider per-compartment font colour from EA theme or element-level colour data

---

## Summary: Priority Matrix

| # | Gap | Severity | Data Available? | Rendering Exists? | Effort |
|---|-----|----------|----------------|-------------------|--------|
| 1 | Attributes on canvas nodes | CRITICAL | Yes (element data) | Yes (UmlRenderer) | Low — thread data through |
| 2 | UML arrowheads/markers | CRITICAL | N/A (type-based) | No | Medium — SVG defs + wiring |
| 3 | Cardinality labels | HIGH | Yes (edge data) | No | Medium — endpoint label component |
| 4 | Role name labels | HIGH | Yes (edge data) | No | Medium — same component as #3 |
| 5 | Orthogonal routing with waypoints | MEDIUM | No (t_diagramlinks not read) | Partial (step routing) | High — proprietary format parsing |
| 6 | Diagram frame | LOW | Yes (diagram name/type) | No | Low |
| 7 | Note styling | LOW | Yes | Partial | Low |
| 8 | Visibility markers + attr font colour | MEDIUM | Yes (Scope field) | Partial | Low |

---

## Recommended Implementation Plan

### Phase 1: "Looks Like EA" (Gaps 1, 2, 8) — Highest visual impact

**Goal:** Class nodes look correct with attributes, and edges are visually distinguishable.

1. **Thread attributes to canvas nodes** — In `service.py`, copy `element_data["attributes"]` into `node_data["attributes"]` during diagram node creation.
2. **Add visibility markers** — In `UmlRenderer.svelte`, prepend scope-based visibility prefix (`+`/`-`/`#`/`~`) to attribute display.
3. **Define SVG markers** — Create `<defs>` block with UML marker definitions (filled diamond, open diamond, closed triangle, open arrow) in `UnifiedCanvas.svelte`.
4. **Wire markers to edges** — Set `markerEnd`/`markerStart` on edge data based on relationship type during import or in edge components.

### Phase 2: "Reads Like EA" (Gaps 3, 4) — Connector annotations

**Goal:** All the text information that appears on connectors in EA is visible in Iris.

1. **Edge endpoint labels component** — New Svelte component that renders cardinality + role name labels at source and target ends of edges.
2. **Position calculation** — Labels positioned near endpoints, offset perpendicular to edge path.
3. **View config integration** — Respect `show_cardinality` and `show_role_names` flags.

### Phase 3: "Routes Like EA" (Gap 5) — Exact path reproduction

**Goal:** Connector paths match EA's orthogonal routing.

1. **Read `t_diagramlinks`** — Add reader for this table with Geometry field parsing.
2. **Parse EA geometry format** — Decode waypoints from EA's proprietary `Geometry` string.
3. **Custom edge paths** — Render edges with imported waypoints instead of algorithm-generated paths.
4. This is the hardest phase and could be deferred if phases 1-2 deliver sufficient fidelity.

### Phase 4: Polish (Gaps 6, 7)

- Diagram frame rendering
- Note styling refinements

---

## What v2.3.0 Actually Fixed

For context on what was already addressed:

| Feature | v2.3.0 Status |
|---------|--------------|
| Element background/border/font colours from EA | Working — `build_node_visual()` extracts and applies |
| Per-diagram colour overrides (ObjectStyle) | Working — priority cascade correct |
| Explicit element dimensions (width/height from EA coordinates) | Working — stored in visual overrides |
| Edge line colour from EA | Working — `build_edge_visual()` extracts |
| Edge dash patterns | Working — LineStyle mapped to CSS dash arrays |
| Theme system with Sparx EA seed theme | Working — tan/cream class backgrounds |
| Stereotype threading for theme resolution | Working — stored in node data |

**In summary:** v2.3.0 solved the **colour and sizing** problem. The remaining gaps are about **structural UML notation** (attributes, markers, labels) and **connector geometry** (routing, waypoints).

---

## References

- `backend/app/import_sparx/service.py` — main import orchestrator
- `backend/app/import_sparx/converter.py` — colour/coordinate conversion
- `backend/app/import_sparx/reader.py` — EA database readers
- `frontend/src/lib/canvas/renderers/UmlRenderer.svelte` — UML node rendering
- `frontend/src/lib/canvas/renderers/UmlEdgeRenderer.svelte` — UML edge rendering
- `frontend/src/lib/canvas/BaseEdge.svelte` — shared edge logic
- `frontend/src/lib/canvas/utils/visualStyles.ts` — visual override CSS generation
- `frontend/src/lib/stores/viewStore.svelte.ts` — view configuration flags
- `docs/analysis/sparxea-package-gap-analysis.md` — prior gap analysis
