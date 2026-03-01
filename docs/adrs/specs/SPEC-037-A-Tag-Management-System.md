# SPEC-037-A: Tag Management System Implementation

**ADR:** [ADR-037](../ADR-037-Tag-Management-System.md)

## Overview

Complete tag management for both entities and models, with a reusable frontend component, list page filtering, and display-only tag inheritance.

## Backend Changes

### Migration: m009_model_tags

Create `model_tags` table mirroring `entity_tags`:
- `model_id TEXT NOT NULL` (FK → models.id)
- `tag TEXT NOT NULL`
- `created_at TEXT NOT NULL`
- `created_by TEXT`
- `PRIMARY KEY (model_id, tag)`

### Model Tag Endpoints

- `POST /api/models/{id}/tags` — Add tag (body: `{ "tag": "string" }`)
- `DELETE /api/models/{id}/tags/{tag}` — Remove tag
- `GET /api/tags/all` — Return all unique tags from both entity_tags and model_tags

### ModelResponse Schema

Add `tags: list[str] = Field(default_factory=list)` to `ModelResponse`.

### Service Layer

- `get_model()`: Include tags query
- `list_models()`: Include tags for each model
- Model tag CRUD in router (following entity tag pattern)

## Frontend Changes

### TagInput Component

Reusable `TagInput.svelte`:
- Props: `tags: string[]`, `onaddtag: (tag: string) => void`, `onremovetag: (tag: string) => void`, `inheritedTags?: string[]`, `readonly?: boolean`
- Renders existing tags as removable pills
- Input field with add button
- Inherited tags shown in lighter style, non-removable
- DOMPurify sanitization on input

### Detail Pages

- Entity detail: TagInput in details tab
- Model detail: TagInput in overview tab

### List Page Filtering

- Entity list: Tag filter dropdown populated from `GET /api/tags/all`
- Model list: Tag filter dropdown next to type filter

## Acceptance Criteria

1. Model tags can be added and removed via API
2. ModelResponse includes tags array
3. TagInput component renders on entity and model detail pages
4. Tags can be added/removed from the UI
5. List pages have tag filter dropdown
6. Inherited tags displayed but non-removable
7. All inputs sanitized with DOMPurify
