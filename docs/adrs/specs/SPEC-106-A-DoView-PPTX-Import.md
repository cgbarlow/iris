# SPEC-106-A: DoView PPTX Import

**ADR:** [ADR-106](../ADR-106-DoView-PPTX-Import.md)
**Part:** A — DoView PPTX import pipeline
**Status:** Draft

---

## Overview

Adds a DoView-specific PPTX import module to Iris, enabling one-click import of DoView models authored in PowerPoint (.pptx) into the Iris element/diagram model. The module uses `python-pptx` for parsing, heuristic shape classification for element typing, and a four-pass pipeline following the established import_sparx pattern.

---

## DoView Compliance Validation

Before any shape parsing occurs, the uploaded PPTX file is validated to confirm it contains a structurally valid DoView model.

### Hard-Fail Criteria

| # | Criterion | Check | Error Message |
|---|-----------|-------|---------------|
| 1 | **Minimum slide count** | `len(prs.slides) >= 3` | "DoView models require at least 3 slides (overview + final outcomes + outcomes maps). Found {n}." |
| 2 | **Overview slide present** | Slide 1 contains >= 2 shapes with `click_action.hyperlink` targeting other slides | "Slide 1 does not appear to be a DoView overview (no internal navigation links found)." |
| 3 | **Final outcomes slide present** | Slide 2 contains >= 2 white/near-white filled rectangles (RGB distance from #FFFFFF < 30) arranged vertically (y-coordinates differ, x-coordinates similar) | "Slide 2 does not appear to contain final outcomes (no white outcome boxes found)." |
| 4 | **Outcomes map slide present** | At least one slide in positions 3+ contains >= 4 colored rectangles with x-positions spanning >= 2 distinct columns (column detection: x-positions clustered within 50px tolerance) | "No outcomes map slides found (slides 3+ do not contain columnar layouts)." |

### Warning-Level Checks

| # | Check | Warning Message |
|---|-------|-----------------|
| 1 | **Title shape presence** | Each slide has a shape with `shape.has_text_frame` and `shape.text` matching the slide title placeholder | "Slide {n} has no title shape; diagram name will be auto-generated." |
| 2 | **Consistent color palette** | Fill colors across outcome boxes fall within the DoView 10-color palette (RGB distance < 40 from any palette color) | "Slide {n} contains non-standard fill colors; imported colors may not match DoView theme." |
| 3 | **Arrow shape count** | Outcomes map slides contain at least 1 arrow auto-shape (`MSO_AUTO_SHAPE_TYPE.RIGHT_ARROW` or chevron) | "Slide {n} has no arrow shapes; causal links will not be inferred for this slide." |

---

## Shape Classification Rules

Each shape on each slide is classified into a DoView element type based on the slide context and shape properties.

### Classification Table

| Slide Type | Shape Pattern | Classification | Notes |
|------------|--------------|----------------|-------|
| Overview (slide 1) | Rectangle with internal hyperlink | `overview_tile` | `linkedDiagramId` resolved in pass 4 |
| Overview (slide 1) | Rectangle, white/near-white fill, no hyperlink | `final_outcome` | Typically the raised "Final Outcomes" summary box |
| Overview (slide 1) | Text-only shape (no fill, no border) | *skipped* | Title or decorative text |
| Final Outcomes (slide 2) | Rectangle, white/near-white fill (RGB distance from #FFFFFF < 30) | `final_outcome` | Vertical stacking preserved in y-coordinates |
| Final Outcomes (slide 2) | Rectangle, colored fill | `outcome_box` | Occasionally present as supporting context |
| Final Outcomes (slide 2) | Shape in footer region (y > 85% of slide height) | `source_reference` | Source citations at bottom of slide |
| Outcomes Map (slides 3+) | Rectangle, colored fill | `outcome_box` | Column position determines causal ordering |
| Outcomes Map (slides 3+) | Rectangle, white/near-white fill | `final_outcome` | Usually in rightmost column |
| Outcomes Map (slides 3+) | `rightArrow` or `chevron` auto-shape | *causal link marker* | Not imported as a node; used to infer `causal_link` edges between adjacent columns |
| Outcomes Map (slides 3+) | Shape in footer region | `source_reference` | Source citations at bottom of slide |
| Any slide | Group shape | *recursed* | Children are individually classified |
| Any slide | Image, freeform, connector | *skipped* | Not part of DoView element model |

---

## Import Pipeline

### Pass 1: Validate

```
Input:  UploadedFile (.pptx)
Output: ValidationResult { valid: bool, errors: str[], warnings: str[] }
```

- Open file with `python-pptx.Presentation(file)`
- Run all 4 hard-fail criteria; collect errors
- Run all 3 warning-level checks; collect warnings
- If any hard-fail errors exist, return `valid=false` with error list
- Otherwise return `valid=true` with any warnings

### Pass 2: Parse & Classify

```
Input:  Presentation object (from python-pptx)
Output: List[SlideData] where SlideData = {
            slide_index: int,
            slide_title: str | None,
            diagram_type: "overview" | "outcomes_map",
            shapes: List[ClassifiedShape]
        }
        ClassifiedShape = {
            shape_id: str,
            element_type: DoViewElementType | "causal_link_marker" | "skip",
            text: str,
            x_emu: int, y_emu: int, w_emu: int, h_emu: int,
            fill_color: str | None,  # hex RGB
            hyperlink_slide_index: int | None,
        }
```

- Iterate each slide; determine slide type by position (1=overview, 2=final outcomes, 3+=outcomes map)
- For each shape in `slide.shapes`, apply classification rules from the table above
- Extract text content via `shape.text_frame.text` (joining paragraphs with newlines)
- Extract fill color via `shape.fill.fore_color.rgb` (handling `None` for no-fill shapes)
- Extract hyperlink target via `shape.click_action.hyperlink.address` or `shape.click_action.target_slide`
- Record EMU coordinates: `shape.left`, `shape.top`, `shape.width`, `shape.height`

### Pass 3: Create Entities & Diagrams

```
Input:  List[SlideData], target set_id, user_id
Output: List[CreatedDiagram], List[CreatedEntity], List[CreatedRelationship]
```

For each `SlideData`:

1. **Create diagram** — type = `overview` or `outcomes_map`, notation = `doview`, name = slide title or "Overview" / "Outcomes Map {n}"
2. **Create entities** — one per classified shape (excluding `skip` and `causal_link_marker`):
   - `entity_type` from classification
   - `name` from shape text (truncated to 200 chars)
   - `visual` override: `{ "bgColor": fill_color }` if fill color differs from theme default
3. **Build canvas_data** — nodes positioned using converted coordinates (see Coordinate Conversion below)
4. **Infer causal links** (outcomes map slides only):
   - Detect columns by clustering shape x-center positions (tolerance: 50px after conversion)
   - For each `causal_link_marker` arrow shape, identify its source column (leftmost column overlapping arrow x-start) and target column (rightmost column overlapping arrow x-end)
   - Create `causal_link` relationships from every entity in the source column to every entity in the target column
   - If no arrow shapes exist on a slide, no causal links are created for that slide
5. **Create relationships** — persist `causal_link` edges in entity_relationships table and in diagram canvas_data edges

### Pass 4: Resolve Cross-Links

```
Input:  List[SlideData], slide_index → diagram_id mapping
Output: Updated overview_tile nodes with linkedDiagramId
```

- For each `overview_tile` node that has a `hyperlink_slide_index`:
  - Look up the diagram created from that slide index
  - Set `node.data.linkedDiagramId = diagram_id` in the overview diagram's canvas_data
  - Update the overview diagram's canvas_data in the database

---

## Canvas Data Format

### Node Structure

```json
{
  "id": "pptx-{slide_index}-{shape_index}",
  "type": "custom",
  "position": { "x": 120, "y": 80 },
  "data": {
    "label": "Improved Teacher Training",
    "entityId": "uuid-...",
    "entityType": "outcome_box",
    "notation": "doview",
    "visual": {
      "bgColor": "#FFF2CC",
      "borderColor": "#D6B656",
      "width": 180,
      "height": 60
    },
    "linkedDiagramId": null
  }
}
```

### Edge Structure

```json
{
  "id": "pptx-edge-{source_id}-{target_id}",
  "source": "pptx-3-0",
  "target": "pptx-3-4",
  "type": "default",
  "data": {
    "relationshipId": "uuid-...",
    "relationshipType": "causal_link",
    "notation": "doview"
  }
}
```

---

## Coordinate Conversion

PowerPoint uses English Metric Units (EMU) internally. Conversion to Iris canvas pixel coordinates:

```
1 inch = 914400 EMU
1 inch = 96 px (at 96 DPI, Iris canvas standard)

px = emu / 914400 * 96
px = emu / 9525
```

**Conversion function:**

```python
def emu_to_px(emu: int) -> int:
    """Convert EMU (English Metric Units) to pixels at 96 DPI."""
    return round(emu / 9525)
```

**Standard PowerPoint slide dimensions:**
- Width: 12192000 EMU = 1280 px
- Height: 6858000 EMU = 720 px

Node positions are converted directly. No additional scaling or offset is applied; the canvas viewport auto-fits to content on load.

---

## API Endpoint

### `POST /api/import/pptx`

**Authentication:** Required (standard session auth)
**Content-Type:** `multipart/form-data`

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | Yes | The .pptx file to import |
| `set_id` | UUID | Yes | Target set for imported diagrams and entities |

**Response (200 OK):**

```json
{
  "status": "success",
  "diagrams_created": 12,
  "entities_created": 87,
  "relationships_created": 134,
  "warnings": [
    "Slide 5 has no arrow shapes; causal links will not be inferred for this slide.",
    "Slide 8 contains non-standard fill colors; imported colors may not match DoView theme."
  ],
  "diagrams": [
    {
      "id": "uuid-...",
      "name": "Overview",
      "diagram_type": "overview",
      "slide_index": 1
    }
  ]
}
```

**Error Responses:**

| Status | Condition | Body |
|--------|-----------|------|
| 400 | File is not a valid .pptx | `{ "error": "Invalid file format. Expected a .pptx file." }` |
| 400 | DoView compliance validation failed | `{ "error": "DoView validation failed", "details": ["error1", "error2"] }` |
| 404 | Set not found | `{ "error": "Set not found." }` |
| 413 | File exceeds size limit (50 MB) | `{ "error": "File too large. Maximum size is 50 MB." }` |

---

## Backend Changes

### New Module: `backend/app/import_pptx/`

```
backend/app/import_pptx/
    __init__.py
    router.py          # FastAPI router for POST /api/import/pptx
    service.py          # Orchestrates the 4-pass pipeline
    validator.py        # Pass 1: DoView compliance validation
    parser.py           # Pass 2: Shape extraction and classification
    creator.py          # Pass 3: Entity/diagram/relationship creation
    linker.py           # Pass 4: Cross-diagram hyperlink resolution
    models.py           # Pydantic models (SlideData, ClassifiedShape, etc.)
    constants.py        # Color palette, EMU conversion, thresholds
```

### `backend/app/main.py`

Register the import_pptx router:

```python
from app.import_pptx.router import router as import_pptx_router
app.include_router(import_pptx_router, prefix="/api/import", tags=["import"])
```

### `requirements.txt` / `pyproject.toml`

Add optional dependency:

```
python-pptx>=0.6.23
```

---

## Frontend Changes

### Import Dialog Enhancement

Add a "DoView PPTX" option to the existing import dialog (alongside SparxEA .qea/.eap):

- File picker filtered to `.pptx` extension
- Set selector (required) for target set
- "Import" button triggers `POST /api/import/pptx`
- Progress indicator during upload and processing
- Results summary dialog showing diagrams created, entities created, relationships created, and any warnings
- "Go to Overview" button navigating to the imported overview diagram

### Navigation

After successful import, the set's diagram list refreshes to show all newly created diagrams. The overview diagram is highlighted as the entry point.

---

## Test Coverage

### Backend Tests

- `backend/tests/test_import_pptx/test_validator.py`
  - Valid DoView PPTX passes all 4 hard-fail criteria
  - PPTX with < 3 slides fails criterion 1
  - PPTX with no hyperlinks on slide 1 fails criterion 2
  - PPTX with no white rectangles on slide 2 fails criterion 3
  - PPTX with no columnar layout on slides 3+ fails criterion 4
  - Warning-level checks produce warnings without blocking import
- `backend/tests/test_import_pptx/test_parser.py`
  - Overview tile classification (rectangle + hyperlink on slide 1)
  - Final outcome classification (white rectangle on slide 2)
  - Outcome box classification (colored rectangle on outcomes map slide)
  - Source reference classification (footer-region shape)
  - Arrow shapes classified as causal link markers
  - Group shapes are recursed
  - Images and freeforms are skipped
- `backend/tests/test_import_pptx/test_creator.py`
  - Diagram creation with correct types and notation
  - Entity creation with correct element types and names
  - Visual override preservation (fill colors)
  - Column detection and causal link inference
  - All-to-all linking between adjacent columns
  - EMU to pixel coordinate conversion
- `backend/tests/test_import_pptx/test_linker.py`
  - Hyperlink slide index resolves to correct diagram ID
  - `linkedDiagramId` set on overview_tile nodes
  - Missing hyperlink targets produce warnings (not errors)
- `backend/tests/test_import_pptx/test_service.py`
  - End-to-end import of a test DoView PPTX fixture
  - Correct diagram count, entity count, relationship count
  - API endpoint returns expected response shape
- `backend/tests/test_import_pptx/test_coordinates.py`
  - `emu_to_px(914400)` == 96
  - `emu_to_px(0)` == 0
  - Standard slide dimensions convert correctly (12192000 -> 1280, 6858000 -> 720)

### Frontend Tests

- `frontend/tests/unit/importPptx.test.ts`
  - Import dialog shows DoView PPTX option
  - File picker accepts only .pptx files
  - Successful import displays results summary
  - Validation errors displayed to user
  - Warnings displayed without blocking
