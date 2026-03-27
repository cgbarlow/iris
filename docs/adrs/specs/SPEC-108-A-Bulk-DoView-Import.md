# SPEC-108-A: Bulk DoView Import

**ADR:** [ADR-108](../ADR-108-Bulk-DoView-PPTX-Import.md)
**Part:** A — Bulk DoView PPTX import endpoint and frontend
**Status:** Draft

---

## Overview

Adds a batch PPTX import endpoint (`POST /api/import/pptx/batch`) that accepts multiple DoView PPTX files in a single multipart upload, iterates over the existing single-file import pipeline (ADR-107 / SPEC-107-A), and returns an aggregated `PptxBatchImportSummary` with per-file results. The frontend is enhanced with a multi-file upload dialog showing per-file progress and aggregated results.

---

## API Endpoint

### `POST /api/import/pptx/batch`

**Authentication:** Required (standard session auth)
**Content-Type:** `multipart/form-data`

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `files[]` | File[] | Yes | One or more .pptx files to import |
| `set_id` | UUID | Yes | Target set for all imported diagrams and entities |

**Response (200 OK — at least one file succeeded):**

```json
{
  "status": "partial_success",
  "total_files": 5,
  "succeeded": 4,
  "failed": 1,
  "total_diagrams_created": 48,
  "total_entities_created": 312,
  "total_relationships_created": 567,
  "results": [
    {
      "filename": "Health-Programme.pptx",
      "status": "success",
      "diagrams_created": 12,
      "entities_created": 87,
      "relationships_created": 134,
      "warnings": [
        "Slide 5 has no arrow shapes; causal links will not be inferred for this slide."
      ],
      "errors": []
    },
    {
      "filename": "Invalid-File.pptx",
      "status": "failed",
      "diagrams_created": 0,
      "entities_created": 0,
      "relationships_created": 0,
      "warnings": [],
      "errors": [
        "DoView validation failed: Slide 1 does not appear to be a DoView overview (no internal navigation links found)."
      ]
    }
  ]
}
```

**Status field values:**

| Value | Meaning |
|-------|---------|
| `"success"` | All files imported successfully |
| `"partial_success"` | At least one file succeeded and at least one failed |
| `"failed"` | All files failed |

**Error Responses:**

| Status | Condition | Body |
|--------|-----------|------|
| 400 | All files failed validation or import | `{ "status": "failed", "total_files": N, "succeeded": 0, "failed": N, "results": [...] }` |
| 404 | Set not found | `{ "error": "Set not found." }` |
| 413 | Total upload size exceeds limit (200 MB) | `{ "error": "Total upload size too large. Maximum is 200 MB." }` |
| 422 | No files provided | `{ "error": "No files provided. Upload at least one .pptx file." }` |

---

## Pydantic Models

### `PptxFileImportResult`

```python
class PptxFileImportResult(BaseModel):
    filename: str
    status: Literal["success", "failed"]
    diagrams_created: int = 0
    entities_created: int = 0
    relationships_created: int = 0
    warnings: list[str] = []
    errors: list[str] = []
```

### `PptxBatchImportSummary`

```python
class PptxBatchImportSummary(BaseModel):
    status: Literal["success", "partial_success", "failed"]
    total_files: int
    succeeded: int
    failed: int
    total_diagrams_created: int
    total_entities_created: int
    total_relationships_created: int
    results: list[PptxFileImportResult]
```

---

## Backend Changes

### `backend/app/import_pptx/router.py`

Add new endpoint:

```python
@router.post("/pptx/batch", response_model=PptxBatchImportSummary)
async def import_pptx_batch(
    files: list[UploadFile] = File(..., alias="files[]"),
    set_id: UUID = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PptxBatchImportSummary:
    ...
```

### `backend/app/import_pptx/service.py`

Add batch orchestration function:

```python
async def import_pptx_batch(
    files: list[UploadFile],
    set_id: UUID,
    db: AsyncSession,
    user_id: UUID,
) -> PptxBatchImportSummary:
    results: list[PptxFileImportResult] = []
    for file in files:
        try:
            result = await import_single_pptx(file, set_id, db, user_id)
            results.append(PptxFileImportResult(
                filename=file.filename,
                status="success",
                diagrams_created=result.diagrams_created,
                entities_created=result.entities_created,
                relationships_created=result.relationships_created,
                warnings=result.warnings,
            ))
        except PptxImportError as e:
            results.append(PptxFileImportResult(
                filename=file.filename,
                status="failed",
                errors=e.details,
            ))
    return _build_summary(results)
```

### `backend/app/import_pptx/models.py`

Add `PptxFileImportResult` and `PptxBatchImportSummary` models as defined above.

### Package Isolation

Each file in the batch creates its own package within the target set, following the same behaviour as the single-file import. This means a batch of 5 files produces 5 separate packages, each containing the diagrams and entities from one PPTX file.

---

## Frontend Changes

### Multi-File Upload Dialog

Enhance the existing import dialog to support batch import:

- **File picker:** Allow multiple `.pptx` file selection (`accept=".pptx"`, `multiple=true`)
- **File list:** Show selected files with individual status indicators (pending, uploading, success, failed)
- **Set selector:** Required target set picker (same as single-file import)
- **Import button:** Triggers `POST /api/import/pptx/batch` with all selected files
- **Progress indicator:** Show overall batch progress (e.g., "Importing file 3 of 5...")
- **Remove file:** Allow removing individual files from the selection before starting import

### Results Display

After the batch completes, show an aggregated results dialog:

- **Summary bar:** "4 of 5 files imported successfully" with colour coding (green = all success, amber = partial, red = all failed)
- **Per-file accordion:** Expandable rows for each file showing diagrams/entities/relationships created, warnings, and errors
- **Navigate button:** "Go to Set" button to navigate to the target set's diagram list
- **Retry failed:** Option to retry only the failed files

---

## Test Coverage

### Backend Tests

- `backend/tests/test_import_pptx/test_batch_service.py`
  - Batch of 3 valid files: all succeed, summary status = "success"
  - Batch of 3 files where 1 is invalid: 2 succeed, 1 fails, summary status = "partial_success"
  - Batch of 3 invalid files: all fail, summary status = "failed"
  - Each file creates a separate package within the set
  - Aggregated counts match sum of individual file results
  - Per-file warnings are preserved in results
  - Per-file errors include validation failure details
- `backend/tests/test_import_pptx/test_batch_router.py`
  - Endpoint returns 200 when at least one file succeeds
  - Endpoint returns 400 when all files fail
  - Endpoint returns 404 when set_id does not exist
  - Endpoint returns 422 when no files are provided
  - Endpoint returns 413 when total upload exceeds 200 MB

### Frontend Tests

- `frontend/tests/unit/importPptxBatch.test.ts`
  - Multi-file picker allows selecting multiple .pptx files
  - File list displays all selected files with pending status
  - Successful batch shows aggregated success summary
  - Partial failure shows amber summary with per-file details
  - Total failure shows error summary
  - Individual file removal works before import starts
