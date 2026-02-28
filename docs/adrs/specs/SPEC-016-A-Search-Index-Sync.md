# SPEC-016-A: Search Index Synchronisation

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-016-A |
| **ADR Reference** | [ADR-016: Search Index Synchronisation](../ADR-016-Search-Index-Synchronisation.md) |
| **Date** | 2026-02-28 |
| **Status** | Active |

---

## Overview

This specification defines the behaviour of the rebuild_search_index() function and the rollback FTS fix required by ADR-016.

---

## 1. rebuild_search_index()

### 1.1 Location
backend/app/search/service.py

### 1.2 Behaviour
1. Delete all rows from entities_fts and models_fts.
2. Query all non-deleted entities joined with their current version.
3. Insert one row per entity into entities_fts.
4. Query all non-deleted models joined with their current version.
5. Insert one row per model into models_fts.
6. Commit the transaction.

### 1.3 Constraints
- Idempotent: Running rebuild_search_index() multiple times produces the same result.
- Excludes deleted: Soft-deleted entities and models must not appear in FTS tables.
- Null-safe: NULL description stored as empty string in FTS table.

---

## 2. Startup Integration
After await m005_up(db_manager.main_db) in startup.py, call:
await rebuild_search_index(db_manager.main_db)

---

## 3. Rollback FTS Fix
In entities/service.py, rollback_entity() must re-index the entity after commit.

---

## 4. Test Cases
| Test | Description |
|------|-------------|
| test_rebuild_indexes_existing_entities | Direct DB insert findable after rebuild |
| test_rebuild_indexes_existing_models | Direct DB insert findable after rebuild |
| test_rebuild_is_idempotent | Double rebuild produces no duplicates |
| test_rebuild_excludes_deleted | Soft-deleted not in FTS |
| test_rollback_updates_fts_index | Rollback updates FTS to rolled-back name |
