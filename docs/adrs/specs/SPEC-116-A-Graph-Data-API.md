# SPEC-116-A: Graph Data API

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-116-A |
| **ADR** | [ADR-116](../ADR-116-Knowledge-Graph-Visualization.md) |
| **Status** | Approved |
| **Date** | 2026-04-03 |

## Overview

A single endpoint returning all elements as graph nodes and all relationships as graph edges for a scoped set or collection, avoiding N+1 API calls.

## Backend

### Module: `backend/app/graph/`

**Models** (`models.py`):

| Model | Fields |
|-------|--------|
| `GraphNode` | `id`, `name`, `element_type`, `description` (nullable), `relationship_count`, `diagram_usage_count` |
| `GraphEdge` | `id`, `source`, `target`, `relationship_type`, `label` (nullable) |
| `GraphResponse` | `nodes: list[GraphNode]`, `edges: list[GraphEdge]` |

**Endpoint** (`router.py`):

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/api/graph` | Required | `GraphResponse` |

Query parameters:
- `set_id` (optional) — scope to a single set
- `collection_id` (optional) — scope to all sets in a collection
- At least one must be provided (400 otherwise)

**Service** (`service.py`):

Nodes query: join `elements` + `element_versions` filtered by `set_id` (or `set_id IN (SELECT id FROM sets WHERE collection_id = ?)`).

Edges query: join `relationships` + `relationship_versions` where both source and target elements are in scope and not deleted.

Relationship counts computed from the returned edges.

### Router registration

Add `from app.graph.router import router as graph_router` and `app.include_router(graph_router)` in `backend/app/main.py`.

## Tests

**File:** `backend/tests/test_graph/test_api.py`

| Test | Assertion |
|------|-----------|
| `test_graph_requires_auth` | 401 without token |
| `test_graph_requires_scope` | 400 with no set_id/collection_id |
| `test_graph_empty_set` | `{nodes: [], edges: []}` |
| `test_graph_returns_nodes` | Elements appear as nodes |
| `test_graph_returns_edges` | Relationships appear as edges |
| `test_graph_scoped_to_set` | Elements from other sets excluded |
| `test_graph_excludes_deleted` | Soft-deleted elements/relationships excluded |
| `test_graph_collection_scope` | Elements from sets in collection included |
