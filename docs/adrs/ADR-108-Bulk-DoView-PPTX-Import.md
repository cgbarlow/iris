# ADR-108: Bulk DoView PPTX Import

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-108 |
| **Initiative** | Bulk DoView PPTX Import |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-25 |
| **Status** | Approved |
| **Supersedes** | — |
| **Superseded By** | — |
| **Related ADRs** | ADR-107 (DoView PPTX Import) |

---

## ADR (WH(Y) Statement format)

**In the context of** importing multiple DoView PPTX files into Iris, where users commonly have a collection of related DoView models (e.g., one per programme area, department, or strategic theme) that need to be brought into a single set for cross-model analysis and AI-assisted querying,

**facing** the need to batch import multiple DoView PPTX files under a single set, where the current single-file endpoint (`POST /api/import/pptx` from ADR-107) requires sequential manual uploads with no unified progress reporting or per-file error handling, making it impractical to import collections of 5-20 related DoView models efficiently,

**we decided for** a batch endpoint `POST /api/import/pptx/batch` that accepts multiple files via multipart upload (`files[]`) along with a required `set_id`, and iterates over the existing single-file import function for each uploaded file, collecting per-file results into an aggregated `PptxBatchImportSummary` response with partial success semantics (successful imports are committed even if other files in the batch fail),

**and neglected** client-side serial uploads (slower due to per-request overhead, no unified progress tracking, no server-side partial failure handling, and the client must implement its own retry/aggregation logic) and a ZIP-based upload approach (adds packaging complexity for users, obscures individual file identity, and complicates per-file error reporting),

**to achieve** efficient bulk import of multiple DoView PPTX files with per-file error reporting, unified progress tracking, and partial success semantics — enabling users to import an entire collection of related DoView models in a single operation while maintaining clear visibility into which files succeeded and which failed,

**accepting that** partial success semantics mean the caller must inspect per-file results to determine overall success, the batch endpoint increases server memory pressure when processing many large PPTX files simultaneously, and the sequential iteration over the single-file import function means batch import time scales linearly with file count.

---

## Problem Statement

Users who have collections of related DoView PPTX models (e.g., one per programme area or strategic theme) need to import them all into a single Iris set. The existing single-file import endpoint (ADR-107) requires users to upload and import each file individually, with no aggregated progress or error reporting. For collections of 5-20 files, this is tedious and error-prone. A batch import capability is needed that reuses the proven single-file import pipeline while adding multi-file orchestration, per-file error reporting, and partial success handling.

---

## Decision Details

### 1. Batch Endpoint Design

The batch endpoint `POST /api/import/pptx/batch` accepts a standard multipart/form-data request with:

- `files[]` — one or more `.pptx` files (required, minimum 1)
- `set_id` — the target set UUID (required)

The endpoint iterates over each uploaded file, invoking the existing single-file import service function from ADR-107. Each file is processed independently; a failure in one file does not abort processing of subsequent files.

### 2. Partial Success Semantics

The batch endpoint uses partial success semantics:

- Each file's import is wrapped in its own database transaction
- Successfully imported files are committed immediately
- Failed files are rolled back individually and their errors recorded
- The response includes per-file results so the caller can determine which files succeeded and which failed
- The HTTP status is `200 OK` if at least one file succeeded, `400 Bad Request` if all files failed, and `422 Unprocessable Entity` if no valid files were provided

### 3. Reuse of Single-File Pipeline

The batch endpoint does not duplicate any import logic. It calls the same four-pass pipeline (validate, parse & classify, create entities & diagrams, resolve cross-links) from ADR-107 for each file. This ensures consistency between single-file and batch import behaviour, and means any improvements to the single-file pipeline automatically benefit batch imports.

### 4. Per-File Result Reporting

Each file in the batch produces an individual result object containing:

- The original filename
- Success/failure status
- Diagrams created, entities created, and relationships created (on success)
- Errors and warnings (on failure or with warnings)

These per-file results are aggregated into a `PptxBatchImportSummary` response.

---

## Consequences

**Positive:**
- One-click import of multiple DoView PPTX models into a single set
- Reuses the proven single-file import pipeline from ADR-107 without duplication
- Per-file error reporting gives clear visibility into partial failures
- Partial success semantics prevent one bad file from blocking the entire batch
- Aggregated summary simplifies client-side result handling

**Negative / Risks:**
- Sequential processing means batch import time scales linearly with file count
- Large batches of large files increase server memory pressure during processing
- Partial success semantics add complexity for callers who expect all-or-nothing behaviour
- Each file creates its own package within the set, which may produce many packages for large batches

---

## Attribution

The DoView methodology is created by Dr Paul Duignan and is open to use under the [DoView Planning Attribution & Trademark Use Policy](https://www.doviewplanning.org/trademarkuse). This implementation is not created or endorsed by DoViewPlanning.org.
