# SPEC-025-A: Entity Browse Enhancements

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-025-A |
| **ADR Reference** | [ADR-025: Entity Browse Enhancements](../ADR-025-Entity-Browse-Enhancements.md) |
| **Date** | 2026-02-28 |
| **Status** | Active |

---

## Overview

This specification defines the implementation of entity browse enhancements including a backend entity tags system, enriched entity list responses with tags and statistics, and frontend grouping modes with enriched entity cards.

---

## Backend: Entity Tags Schema

### Migration m008_entity_tags

New table `entity_tags`:

| Column | Type | Constraints |
|--------|------|-------------|
| `entity_id` | TEXT | NOT NULL, FK -> entities(id) |
| `tag` | TEXT | NOT NULL, 1-50 characters |
| `created_at` | TEXT | NOT NULL, ISO 8601 |
| `created_by` | TEXT | User ID of creator |

**Primary key:** `(entity_id, tag)` -- each entity-tag pair is unique.

---

## Backend: Tag API Endpoints

All endpoints require authentication (`get_current_user` dependency).

### POST /api/entities/{entity_id}/tags

Add a tag to an entity.

| Field | Details |
|-------|---------|
| Request body | `{ "tag": "string" }` |
| Validation | Tag must be 1-50 characters after trimming |
| Success | 201 with `{ "entity_id", "tag", "created_at" }` |
| Duplicate | 409 Conflict |

### DELETE /api/entities/{entity_id}/tags/{tag}

Remove a tag from an entity.

| Field | Details |
|-------|---------|
| Success | 200 with `{ "status": "ok" }` |
| Idempotent | No error if tag does not exist |

### GET /api/entities/tags/all

List all unique tags across all entities.

| Field | Details |
|-------|---------|
| Response | `string[]` sorted alphabetically |

---

## Backend: Enriched Entity List

The `list_entities()` service function is enhanced to return additional fields for each entity:

| Field | Type | Source |
|-------|------|--------|
| `tags` | `string[]` | `entity_tags` table |
| `relationship_count` | `int` | Count of non-deleted relationships |
| `model_usage_count` | `int` | Count of models referencing the entity |

These fields are added as optional fields on the `EntityResponse` Pydantic model.

---

## Frontend: Grouping Mode

### State

```typescript
let groupMode = $state<'none' | 'type' | 'tag'>('none');
```

Persisted to `localStorage` key `iris-entities-group`.

### Grouping Logic

| Mode | Behaviour |
|------|-----------|
| `none` | Flat list (current behaviour) |
| `type` | Group by `entity_type` |
| `tag` | Group by tag; entities with multiple tags appear in each group; untagged entities in "Untagged" group |

### UI

- Dropdown in the filter toolbar: "Not grouped", "By type", "By tag"
- Groups rendered as collapsible `<details open>` elements with summary showing group name and count
- Ungrouped mode renders flat `<ul>` as before

---

## Frontend: Enriched Entity Cards

Each entity card in the list displays:

| Element | Condition | Style |
|---------|-----------|-------|
| Entity name | Always | `font-medium`, primary colour |
| Type badge | Always | Surface background, muted text |
| Tag badges | When tags present | Primary background, white text |
| Relationship count | When > 0 | Muted text, e.g. "3 rel" |
| Model usage count | When > 0 | Muted text, e.g. "2 models" |
| Description excerpt | When present | Muted text, max 60 chars |

---

## Frontend: Type Updates

The `Entity` interface gains optional fields:

```typescript
tags?: string[];
relationship_count?: number;
model_usage_count?: number;
```

---

## Accessibility

| Requirement | Implementation |
|-------------|----------------|
| Grouping label | `<label>` with `sr-only` class for screen readers |
| Group sections | Native `<details>`/`<summary>` elements (keyboard accessible) |
| Tag badges | Text content readable by screen readers |
| Focus visible | Existing focus indicator styles apply |

---

## Theme Compatibility

All new UI elements use CSS custom properties:

- `--color-border` for card borders
- `--color-fg` for text
- `--color-primary` for names, tags
- `--color-surface` for type badge backgrounds
- `--color-muted` for counts and descriptions
- `--color-bg` for backgrounds

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| 1 | Tags can be added to entities via POST endpoint |
| 2 | Tags can be removed via DELETE endpoint |
| 3 | All unique tags can be listed via GET endpoint |
| 4 | Entity list response includes tags, relationship_count, model_usage_count |
| 5 | Grouping dropdown appears in entity list filter toolbar |
| 6 | "By type" grouping shows collapsible sections per entity type |
| 7 | "By tag" grouping shows collapsible sections per tag |
| 8 | Entity cards show tag badges when tags are present |
| 9 | Entity cards show relationship and model usage counts when > 0 |
| 10 | Grouping preference persists in localStorage |

---

*This specification implements [ADR-025](../ADR-025-Entity-Browse-Enhancements.md).*
