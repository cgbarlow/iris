# SPEC-022-A: PNG Thumbnails

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-022-A |
| **ADR Reference** | [ADR-022: Server-Generated PNG Thumbnails](../ADR-022-Server-Generated-PNG-Thumbnails.md) |
| **Date** | 2026-02-28 |
| **Status** | Active |

---

## Overview

This specification defines the server-side thumbnail generation pipeline, database storage, API endpoint, and frontend toggle for serving PNG thumbnails of model gallery cards.

---

## Database Schema

### Model Thumbnails Table (Migration m007)

```sql
CREATE TABLE IF NOT EXISTS model_thumbnails (
  model_id TEXT PRIMARY KEY,
  thumbnail BLOB NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (model_id) REFERENCES models(id)
);
```

One row per model. Thumbnails are replaced on each model create/update via `INSERT OR REPLACE`.

---

## Backend: Thumbnail Generation Service

**File:** `backend/app/models_crud/thumbnail.py`

### Functions

| Function | Purpose |
|----------|---------|
| `generate_svg_from_model_data(data, model_type)` | Generates SVG string from model data |
| `generate_and_store_thumbnail(db, model_id, data, model_type)` | Generates PNG (or SVG fallback) and stores in database |
| `get_thumbnail(db, model_id)` | Retrieves stored thumbnail bytes |

### SVG Generation Logic

The SVG generator creates a 400x250 SVG with a dark background (`#1e293b`):

- **Sequence models:** Renders participants as labelled boxes along the top with dashed lifelines extending downward.
- **Canvas models:** Renders up to 12 nodes as labelled rounded rectangles, positioned by scaling model coordinates to fit the thumbnail viewport. Draws up to 15 edges as lines between node centres.
- **Empty models:** Renders centred "Empty" text.

### PNG Conversion

Uses `cairosvg.svg2png()` with output dimensions 400x250. If `cairosvg` is not importable, falls back to storing raw SVG bytes. The API endpoint detects the format via PNG magic bytes (`\x89PNG\r\n\x1a\n`).

---

## Backend: API Endpoint

### GET /api/models/{model_id}/thumbnail

Returns the stored thumbnail for a model.

| Aspect | Detail |
|--------|--------|
| **Authentication** | Not required (public endpoint for image serving) |
| **Success Response** | `200` with `image/png` or `image/svg+xml` content type |
| **Not Found** | `404` with `{ "detail": "Thumbnail not found" }` |
| **Cache Header** | `Cache-Control: public, max-age=300` |

Content type is determined by checking the first 8 bytes for the PNG magic number.

---

## Backend: Thumbnail Generation Triggers

### On Model Create (`create_model`)

After the search index commit, call:
```python
await generate_and_store_thumbnail(db, model_id, data, model_type)
```

### On Model Update (`update_model`)

After the search re-index block, call:
```python
await generate_and_store_thumbnail(db, model_id, data, type_row[0])
```

Only generates if `type_row` is available (model exists).

---

## Frontend: Thumbnail Mode Toggle

**File:** `frontend/src/routes/models/+page.svelte`

### Behaviour

1. On mount, fetch `GET /api/settings` to read `gallery_thumbnail_mode`.
2. Store mode in `thumbnailMode` state variable (default: `'svg'`).
3. In gallery view, conditionally render:
   - **SVG mode:** Existing `<ModelThumbnail>` component (client-side SVG)
   - **PNG mode:** `<img>` tag with `src="/api/models/{model.id}/thumbnail"` and `loading="lazy"`

### Fallback

If the settings API call fails (settings not seeded, network error), defaults to `'svg'` mode silently.

---

## Startup Integration

1. Migration `m007_thumbnails` runs after `m005_search` during startup (added to `initialize_databases`).
2. The `model_thumbnails` table is created with `IF NOT EXISTS` for idempotency.

---

## File Inventory

| File | Purpose |
|------|---------|
| `backend/app/migrations/m007_thumbnails.py` | Model thumbnails table migration |
| `backend/app/models_crud/thumbnail.py` | Thumbnail generation, storage, and retrieval |
| `backend/app/models_crud/router.py` | New `GET /{model_id}/thumbnail` endpoint |
| `backend/app/models_crud/service.py` | Thumbnail generation calls in create/update |
| `backend/app/startup.py` | Migration registration |
| `frontend/src/routes/models/+page.svelte` | Conditional PNG/SVG thumbnail rendering |

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| 1 | `model_thumbnails` table created on startup |
| 2 | Thumbnails generated on model create |
| 3 | Thumbnails regenerated on model update |
| 4 | `GET /api/models/{id}/thumbnail` returns image bytes with correct content type |
| 5 | Gallery cards show `<img>` tags when `gallery_thumbnail_mode` is `png` |
| 6 | Gallery cards show `<ModelThumbnail>` when `gallery_thumbnail_mode` is `svg` |
| 7 | System functions without cairosvg (SVG bytes fallback) |

---

*This specification implements [ADR-022](../ADR-022-Server-Generated-PNG-Thumbnails.md).*
