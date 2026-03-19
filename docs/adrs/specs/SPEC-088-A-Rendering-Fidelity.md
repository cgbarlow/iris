# SPEC-088-A: EA Rendering Fidelity Fixes

**ADR:** ADR-088
**Date:** 2026-03-07

## Changes

### Issue 1: Note label deduplication
- **File:** `backend/app/import_sparx/service.py`
- Added `strip_label_from_note(label, note_text)` helper
- Applied when building note node data: strips label prefix + linebreak from description
- **Test:** `test_note_dedup.py` — 6 test cases

### Issue 2: Attribute italic inheritance
- **File:** `frontend/src/lib/canvas/renderers/UmlRenderer.svelte`
- Added `font-style: normal` to `.uml-node__attr` and `.uml-node__compartment` CSS rules

### Issue 3: Fixed node sizing
- **File:** `frontend/src/lib/canvas/renderers/UmlRenderer.svelte`
- Added `hasFixedSize` derived from `data.visual.width/height`
- Passed to `nodeOverrideStyle(data.visual, hasFixedSize)`
- Added `overflow: hidden; box-sizing: border-box` when fixed size

### Issue 4: Composition edge markers
- **File:** `frontend/src/lib/canvas/renderers/UmlEdgeRenderer.svelte`
- Added composition/aggregation to markerEnd when direction is `Source -> Destination`
- **File:** `frontend/src/lib/canvas/uml/UmlMarkerDefs.svelte`
- Changed diamond marker `refX` from `18` to `0` so diamonds extend away from node

### Issue 5: Handle routing
- **File:** `frontend/src/lib/canvas/renderers/UmlRenderer.svelte`, `nodes/NoteNode.svelte`
- Added dual-type handles: each side gets both source and target handle
- **File:** `backend/app/import_sparx/service.py`
- Added `compute_auto_handles()` based on relative node center positions
- Applied when Start_Edge=0 AND End_Edge=0 (EA auto-route)
- **Test:** `test_auto_handles.py` — 6 test cases

### Issue 6: Edge label positions
- **File:** `backend/app/import_sparx/converter.py`
- Extended `parse_diagram_link_geometry()` to extract LLB/LLT/LRT/LRB CX:CY values
- **File:** `backend/app/import_sparx/service.py`
- Stored parsed label positions in edge data as `labelPositions`
- **File:** `frontend/src/lib/canvas/edges/EdgeEndpointLabels.svelte`
- Accepts `labelPositions` prop; uses data-driven offsets when available
- **File:** `frontend/src/lib/types/canvas.ts`
- Added `labelPositions` typed field to `CanvasEdgeData`
- **Test:** `test_geometry_parser.py` — 5 new test cases for label parsing

### Issue 7: Diagram frame as canvas node
- **File:** `frontend/src/lib/canvas/nodes/DiagramFrameNode.svelte` (new)
- SVG-based non-interactive node with border + title tab
- **File:** `frontend/src/lib/canvas/DynamicNode.svelte`
- Registered `diagram_frame` node type
- **File:** `frontend/src/lib/canvas/UnifiedCanvas.svelte`
- Removed old DiagramFrame import and rendering; removed `diagramFrame` prop
- **File:** `frontend/src/routes/diagrams/[id]/+page.svelte`
- Removed `diagramFrame` derived value and 4 prop-passing locations
- **File:** `backend/app/import_sparx/service.py`
- Emits frame as a `diagram_frame` node at bounding-box origin with padding
- **Test:** `test_diagram_frame.py` — rewritten: 4 tests verify frame is a node

### Issue 8: Node content clipping (R3)
- **File:** `frontend/src/lib/canvas/renderers/UmlRenderer.svelte`
- Hide UML icon when `hasFixedSize` is true: `{#if !isPackage && !hideIcons && !hasFixedSize}`
- Added `class:uml-node--fixed={hasFixedSize}` to root div
- Compact CSS: `.uml-node--fixed .uml-node__header { padding: 1px 4px; line-height: 1.1 }`
- Compact CSS: `.uml-node--fixed .uml-node__compartment { padding: 1px 4px }`
- Compact CSS: `.uml-node--fixed .uml-node__attr { line-height: 1.2 }`

### Issue 9: Package nodes missing from diagrams (R3)
- **File:** `backend/app/import_sparx/mapper.py`
- Changed `"Package": "_package"` to `"Package": "package_uml"`
- **File:** `backend/app/import_sparx/service.py`
- Removed `if iris_type == "_package": continue` skip
- Package elements now created as regular Iris elements, appear in `element_map`
- Package-to-package connectors automatically become canvas edges

### Issue 10: Diagram frame type label (R3)
- **File:** `backend/app/import_sparx/service.py`
- Changed `frameType` from raw `diag.Diagram_Type` to mapped `diagram_type`
- **File:** `backend/app/import_sparx/mapper.py`
- Changed `"Package": ("component", "uml")` to `"Package": ("pkg", "uml")`
