# ADR-037: Tag Management System

## Status

Accepted

## Context

### What is the problem?

Entities have a `entity_tags` table (m008) with backend API endpoints for adding/removing tags, but:
1. There is no frontend UI for managing tags on entities.
2. Models cannot be tagged at all — no `model_tags` table exists.
3. No tag filter dropdown exists on list pages.
4. No tag inheritance (entity showing tags from its models, and vice versa).

### Why does it matter?

Tags are a fundamental organizational tool for enterprise architecture repositories. Without proper tag support, users cannot categorize, filter, or discover entities and models efficiently.

### How did we get here?

Entity tags were added as a backend-only feature in m008. The frontend was not built to surface them.

## Decision

Implement a complete tag management system:

1. **Backend**: Add `model_tags` table (m009 migration), model tag API endpoints, include tags in model responses.
2. **Frontend**: Create a reusable `TagInput` component for adding/removing tags on entity and model detail pages.
3. **Filtering**: Add tag filter dropdowns on entity and model list pages.
4. **Tag inheritance** (display-only): Entities show inherited tags from their models; models show inherited tags from their entities. Inherited tags are visually distinct and non-removable.
5. **Global tags endpoint**: `GET /api/tags/all` already exists for entities; add model tags to the aggregation.

## Rejected Alternatives

1. **Hierarchical tag taxonomy** — Over-engineered for current needs. Flat tags with free-text input are simpler and more flexible.
2. **Separate tag management admin page** — Tags are best managed inline on detail pages where context is clear.
3. **Backend-computed tag inheritance** — Would require complex queries and denormalization. Client-side computation from already-fetched related resources is simpler and avoids new API endpoints.
