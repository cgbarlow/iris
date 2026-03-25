# SPEC-102-A: Collections

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-102-A |
| **ADR** | [ADR-102](../ADR-102-Collections.md) |
| **Status** | Draft |
| **Date** | 2026-03-24 |

---

## Overview

Collections provide a higher-level grouping for Sets. A Set can optionally belong to one Collection. Collections enable cross-set filtering throughout Iris and multi-set AI context in Ask AI.

## Database Changes

### SQLite Migration (m030)

- New `collections` table: id, name, description, created_at, created_by, updated_at, is_deleted, thumbnail_source, thumbnail_diagram_id, thumbnail_image
- Partial unique index on name (WHERE is_deleted = 0)
- `sets.collection_id` nullable FK to collections(id)
- `ai_conversations.collection_id` nullable FK to collections(id)

### Supabase Migration (m033)

Same schema in PostgreSQL syntax.

## API Endpoints

### Collections CRUD

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/collections` | Create collection |
| GET | `/api/collections` | List all non-deleted with counts |
| GET | `/api/collections/{id}` | Get one with counts |
| PUT | `/api/collections/{id}` | Update |
| DELETE | `/api/collections/{id}` | Soft-delete, unlink sets |
| POST | `/api/collections/{id}/thumbnail` | Upload thumbnail image |
| GET | `/api/collections/{id}/thumbnail` | Get thumbnail |
| GET | `/api/collections/{id}/sets` | List sets in collection |

### Extended Sets API

- GET `/api/sets` accepts `?collection_id=` query param
- SetResponse includes `collection_id` and `collection_name`

### Multi-Set AI

- POST `/api/ai/ask` accepts `set_ids[]` and optional `collection_id`
- Builds context from multiple sets with proportional token budget

## Frontend Changes

### Components
- `CollectionSelector` — dropdown mirroring SetSelector
- `CollectionDialog` — create/edit modal
- `MultiSetSelector` — multi-checkbox set picker for Ask AI

### Pages
- `/collections` — list/gallery with thumbnails
- `/collections/[id]` — detail/edit page

### Navigation
- Collections nav item between Ask AI and Sets
- Header breadcrumb: Iris / Collection / Set

### Dashboard
- 4-column stats: Collections | Sets | Diagrams | Elements
- Collection inferred from active set's collection_id

### Filters
- Collection dropdown on Diagrams and Elements pages
- Ask AI: Collection dropdown + multi-set selector

## Acceptance Criteria

1. Collections CRUD works end-to-end with thumbnails
2. Sets can be assigned to a collection via edit page
3. Deleting a collection unlinks its sets (sets survive)
4. Collection filter cascades to set filter on Diagrams/Elements pages
5. Ask AI supports multi-set selection with or without collection
6. Header shows Collection / Set breadcrumb when both active
7. Dashboard shows 4-column stats with collection card
8. Collection pill appears under set names on Sets page
