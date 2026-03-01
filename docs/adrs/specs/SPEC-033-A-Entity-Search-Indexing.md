# SPEC-033-A: Entity Search Indexing Verification

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-033-A |
| **ADR Reference** | [ADR-033: Search Display Fix](../ADR-033-Search-Display-Fix.md) |
| **Date** | 2026-03-01 |
| **Status** | Active |

---

## Overview

This specification defines the expected behaviour of entity search indexing during CRUD operations and the regression tests that verify it. It extends SPEC-016-A (which covers startup rebuild and rollback re-indexing) to cover incremental indexing during create, update, and delete operations.

---

## 1. Incremental Indexing Requirements

### 1.1 Create Entity

When `create_entity()` is called in `backend/app/entities/service.py`:

1. The entity and entity_version records are inserted and committed.
2. `index_entity()` from `backend/app/search/service.py` is called with the entity's id, name, entity_type, and description.
3. The FTS index is committed.
4. The entity is immediately searchable by name and description without requiring a `rebuild_search_index()` call.

### 1.2 Update Entity

When `update_entity()` is called:

1. The entity version is incremented and new version record is inserted and committed.
2. The entity_type is fetched from the entities table.
3. `index_entity()` is called with the updated name and description, which deletes the old FTS entry and inserts a new one.
4. The FTS index is committed.
5. The entity is immediately searchable by its new name/description, and the old name/description is no longer matched.

### 1.3 Delete Entity

When `soft_delete_entity()` is called:

1. The entity is marked as deleted (is_deleted = 1) and committed.
2. `remove_entity_index()` is called, which deletes the entity's row from `entities_fts`.
3. The FTS index is committed.
4. The entity is no longer searchable.

### 1.4 Rollback Entity

Covered by SPEC-016-A. When `rollback_entity()` is called, the FTS index is updated with the rolled-back version's name and description.

---

## 2. Index Functions

### 2.1 index_entity()

Location: `backend/app/search/service.py`

Behaviour:
1. DELETE FROM entities_fts WHERE entity_id = ?
2. INSERT INTO entities_fts (entity_id, name, entity_type, description) VALUES (?, ?, ?, ?)
3. NULL descriptions are stored as empty strings.

This delete-then-insert pattern ensures idempotency.

### 2.2 remove_entity_index()

Location: `backend/app/search/service.py`

Behaviour:
1. DELETE FROM entities_fts WHERE entity_id = ?

---

## 3. Parallel Model Pattern

The entity indexing follows the identical pattern used in the model service:

| Operation | Entity Service | Model Service |
|-----------|---------------|---------------|
| Create | `create_entity()` calls `_index_entity()` | `create_model()` calls `_index_model()` |
| Update | `update_entity()` calls `_index_entity()` | `update_model()` calls `_index_model()` |
| Delete | `soft_delete_entity()` calls `_remove_entity_index()` | `soft_delete_model()` calls `_remove_model_index()` |
| Rollback | `rollback_entity()` calls `_index_entity()` | N/A (models have no rollback) |

---

## 4. Test Cases

All tests are in `backend/tests/test_search/test_entity_indexing.py`.

| Test | Description | Verifies |
|------|-------------|----------|
| test_create_entity_indexes_for_search | Create entity via service, search by name | 1.1 |
| test_create_entity_searchable_by_description | Create entity, search by description text | 1.1 |
| test_update_entity_updates_search_index | Update entity name, verify new name searchable, old name not | 1.2 |
| test_delete_entity_removes_from_search_index | Create then delete entity, verify not searchable | 1.3 |
| test_multiple_entities_all_searchable | Create 3 entities, verify all found by common term | 1.1 |
| test_entity_deep_link_format | Verify search result deep_link is /entities/{id} | 1.1 |

---

## 5. Frontend Search Display

The dashboard search at `frontend/src/routes/+page.svelte` correctly handles both result types:

- Calls `GET /api/search?q=...` which returns `SearchResponse` with `results` array
- Each result has `result_type` ("entity" or "model"), `name`, `type_detail`, and `deep_link`
- Results are rendered with a badge showing `{result.result_type} . {result.type_detail}`
- Deep links navigate to `/entities/{id}` or `/models/{id}` respectively

No frontend changes are required.

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Entity created via service is immediately searchable by name | test_create_entity_indexes_for_search |
| Entity created via service is immediately searchable by description | test_create_entity_searchable_by_description |
| Updated entity name is reflected in search results | test_update_entity_updates_search_index |
| Deleted entity is removed from search results | test_delete_entity_removes_from_search_index |
| Multiple entities are all searchable | test_multiple_entities_all_searchable |
| Search results contain correct deep_link format | test_entity_deep_link_format |
| All search tests pass (6 new + 14 existing = 20 total) | pytest tests/test_search/ |

---

*This specification implements [ADR-033](../ADR-033-Search-Display-Fix.md).*
