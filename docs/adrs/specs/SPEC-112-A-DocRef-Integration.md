# SPEC-112-A: DocRef Integration

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-112-A |
| **ADR** | [ADR-112](../ADR-112-DocRef-Legislation-Integration.md) |
| **Status** | Draft |
| **Date** | 2026-03-29 |

## Overview

Integrate legislation.docref.nz as an optional data source extension for the Ask AI feature. Users can browse, import, and select NZ legislation documents to include as context in AI conversations.

## Data Source

- **Index URL:** `https://legislation.docref.nz/`
- **Document URL pattern:** `https://legislation.docref.nz/{slug}/{version}/en/`
- **CSV URL pattern:** `https://legislation.docref.nz/{slug}/{version}/en/{slug}-{version}-en-chunked.csv`
- **CSV columns:** `id` (section identifier), `url` (anchor link), `c` (content text)
- **~54 documents**, latest version only, ~400+ chunks per document

## Database Schema (Migration m034)

### docref_documents

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | UUID |
| slug | TEXT NOT NULL | URL slug (e.g. "social-security-act-2018") |
| title | TEXT NOT NULL | Human-readable title |
| latest_version | TEXT NOT NULL | Date version (e.g. "2025-07-01") |
| source_url | TEXT NOT NULL | Full URL to document page |
| csv_url | TEXT NOT NULL | Full URL to chunked CSV |
| chunk_count | INTEGER DEFAULT 0 | Number of imported chunks |
| status | TEXT DEFAULT 'available' | available, importing, imported, error |
| error_message | TEXT | Error details if status is 'error' |
| imported_at | TEXT | ISO timestamp of successful import |
| imported_by | TEXT | User ID who triggered import |
| created_at | TEXT NOT NULL | First seen in index |
| updated_at | TEXT NOT NULL | Last index refresh |

UNIQUE(slug, latest_version)

### docref_chunks

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | UUID |
| document_id | TEXT NOT NULL FK | References docref_documents(id) ON DELETE CASCADE |
| chunk_id | TEXT NOT NULL | Original CSV `id` column |
| url | TEXT NOT NULL | Anchor link URL |
| content | TEXT NOT NULL | Legislative text |
| sort_order | INTEGER DEFAULT 0 | Row order from CSV |

UNIQUE(document_id, chunk_id)

## API Endpoints

All gated on `require_docref_enabled` dependency.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/docref/refresh | Admin | Scrape DocRef index, upsert documents |
| GET | /api/docref/documents | User | List all known documents with status |
| POST | /api/docref/documents/{id}/import | User | Download CSV and import chunks |
| DELETE | /api/docref/documents/{id}/chunks | Admin | Remove imported chunks, reset status |

## AI Context Integration

`MultiSetQARequest` gains `docref_doc_ids: list[str] | None`. When present and the extension is enabled, `build_docref_context(db, document_ids)` appends legislation text to the set context string.

Context format:
```
LEGISLATION: {title} ({version})
Source: {source_url}

[chunk_id] content
[chunk_id] content
...
```

## Hourly Index Refresh

A background asyncio task runs every 3600 seconds, calling `refresh_document_index()` if the docref extension is enabled. Started in app lifespan, cancelled on shutdown.

## Frontend

### DocRefSelector Component
- Dropdown below Collection selector on Ask AI page
- Shows all documents with status indicators (none=available, spinner=importing, blue tick=imported)
- Click to import, checkbox to select imported docs as AI context
- Only visible when docref extension is enabled

### Ask AI Page Changes
- New state: `selectedDocRefIds`, `docrefEnabled`
- Checks extension status on load via `/api/extensions`
- Passes `docrefDocIds` prop to SetQA

### SetQA Changes
- New `docrefDocIds?: string[]` prop
- Includes `docref_doc_ids` in POST /api/ai/ask request body

### Extensions Admin Page
- DocRef added to KNOWN_EXTENSIONS array
