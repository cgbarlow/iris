# SPEC-115-A: File Upload AI Context

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-115-A |
| **ADR** | [ADR-115](../ADR-115-Session-File-Upload-AI-Context.md) |
| **Status** | Implemented |
| **Date** | 2026-03-30 |

---

## Overview

Session-scoped file upload for Ask AI. Users upload files on the Context tab, backend extracts text and returns it, frontend holds extracted text in state, and includes it in chat requests alongside set and DocRef context.

---

## Backend

### Text Extraction Service

**File:** `backend/app/ai/extract.py`

| Function | Signature | Purpose |
|----------|-----------|---------|
| `extract_text` | `(filename, content, content_type) -> ExtractionResult` | Extract text from file bytes |

**ExtractionResult dataclass:**
- `filename: str`
- `content_type: str`
- `size_bytes: int`
- `extracted_text: str`
- `truncated: bool`
- `error: str | None`

**Supported formats:**

| Format | Library | Strategy |
|--------|---------|----------|
| PDF | pdfplumber | Page-by-page text extraction |
| DOCX | python-docx | Paragraph text concatenation |
| XLSX | openpyxl | Sheet-by-sheet, row-by-row as TSV |
| PPTX | python-pptx | Slide-by-slide shape text |
| CSV | Built-in csv | Row formatting |
| Text/code | UTF-8 decode | Extension allowlist + text/* content types |
| Unknown | UTF-8 fallback | Attempt decode, error if binary |

**Truncation:** 100,000 characters max. Sets `truncated=True`.

### API Endpoint

**`POST /api/ai/files/extract`**

- Auth: Required (any authenticated user)
- Input: `UploadFile` (multipart/form-data)
- Size limit: 5 MB (413 if exceeded)
- Response: `FileExtractResponse`

```json
{
  "filename": "report.pdf",
  "content_type": "application/pdf",
  "size_bytes": 245000,
  "extracted_text": "...",
  "truncated": false,
  "error": null
}
```

### Chat Integration

**Model changes in `backend/app/ai/models.py`:**

```python
class FileContext(BaseModel):
    filename: str
    text: str

class MultiSetQARequest(BaseModel):
    # ... existing fields ...
    file_contexts: list[FileContext] | None = None
```

**Validation:** At least one of `set_ids`, `docref_doc_ids`, or `file_contexts` must be non-empty.

**Context building:** File content appended after set and DocRef context:

```
UPLOADED FILES:
FILE: report.pdf
<extracted text>

---

FILE: data.csv
<extracted text>
```

**System prompt:** When only files are provided (no sets, no docref), uses a generic file-focused prompt. Otherwise includes files alongside existing context types.

---

## Frontend

### FileUploader Component

**File:** `frontend/src/lib/components/FileUploader.svelte`

**Props:**
- `files: UploadedFile[]` — current file list
- `onchange: (files: UploadedFile[]) => void` — update callback

**UploadedFile type:**
- `id: string` (crypto.randomUUID)
- `filename, content_type, size_bytes`
- `extracted_text: string`
- `truncated: boolean`
- `error: string | null`
- `uploading: boolean`

**Features:**
- Drag-and-drop zone with visual feedback
- Click to browse (hidden file input)
- 5 MB client-side size check (immediate error)
- File list with status: Extracting / Ready / Truncated / Error
- Remove button per file

### Ask AI Page Integration

**File:** `frontend/src/routes/ask/+page.svelte`

- FileUploader rendered on Context tab after DocRef selector
- `uploadedFiles` state holds all files
- `readyFiles` derived: non-uploading, non-error files
- `hasContext` includes `readyFiles.length > 0`
- `contextKey` includes ready file IDs
- `contextSummary` includes file names
- `fileContexts` prop passed to SetQA

### SetQA Component

**File:** `frontend/src/lib/components/SetQA.svelte`

- New prop: `fileContexts?: { filename: string; text: string }[]`
- Included in `POST /api/ai/ask` request body as `file_contexts`

---

## Dependencies Added

| Package | Version | Purpose |
|---------|---------|---------|
| pdfplumber | >=0.11.0 | PDF text extraction |
| python-docx | >=1.1.0 | DOCX text extraction |
| openpyxl | >=3.1.0 | XLSX text extraction |

---

## Tests

| Test File | Count | Scope |
|-----------|-------|-------|
| `test_extract.py` | 16 | Extraction unit tests (all file types, truncation, errors) |
| `test_file_upload_router.py` | 5 | Endpoint integration tests (auth, size limit, errors) |
