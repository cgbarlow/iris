# ADR-033: Search Display Fix

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-033 |
| **Initiative** | Search Display Fix (WP-2) |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris search subsystem, where ADR-016 addressed the startup rebuild of FTS5 indices and rollback re-indexing, but the incremental CRUD indexing of entities (create, update, delete) was implemented without explicit test coverage or documentation verifying that entities created after startup are immediately searchable,

**facing** the reported problem that search only showed models and not entities, which required investigation into whether entity CRUD operations correctly call `index_entity()` and `remove_entity_index()` to maintain the FTS5 search index in real time,

**we decided for** verifying the existing incremental entity indexing implementation, adding comprehensive regression tests at the service layer that specifically test entity searchability after create, update, and delete operations (without requiring a full `rebuild_search_index()` call), and documenting the entity indexing pattern as a companion to ADR-016,

**and neglected** adding a separate indexing middleware or event-driven approach (unnecessary given the direct calls already present in the service layer), and modifying the frontend search display logic (the frontend correctly renders both entity and model results when the backend returns them),

**to achieve** documented confidence that entity CRUD operations maintain the FTS5 search index in real time, regression test coverage preventing future indexing gaps, and clear traceability between the entity service layer and the search index,

**accepting that** this ADR primarily documents and tests existing behaviour rather than introducing new code changes, because the incremental indexing was already correctly implemented but lacked dedicated test coverage and documentation.

---

## Investigation Findings

The root cause investigation confirmed:

1. **`create_entity()`** in `backend/app/entities/service.py` correctly calls `_index_entity()` after committing the entity and version records (line 43).
2. **`update_entity()`** correctly re-indexes with the new name and description after update (line 237).
3. **`rollback_entity()`** correctly re-indexes with the rolled-back version data (line 307), as fixed by ADR-016.
4. **`soft_delete_entity()`** correctly calls `_remove_entity_index()` after soft-deleting (line 367).
5. **The frontend dashboard** at `frontend/src/routes/+page.svelte` correctly renders both `entity` and `model` result types from the search API response.
6. **The search service** at `backend/app/search/service.py` queries both `entities_fts` and `models_fts` tables and returns combined results.

The entity indexing follows the identical pattern used in the model service (`backend/app/models_crud/service.py`), which has `_index_model()` calls in `create_model()` and `update_model()`, and `_remove_model_index()` in `soft_delete_model()`.

---

## Options Considered

### Option 1: Add Regression Tests and Documentation (Selected)

**Pros:**
- Verifies the existing implementation works correctly
- Prevents future regressions if entity service code is refactored
- Documents the incremental indexing pattern explicitly
- No code changes required to production code -- minimal risk

**Cons:**
- Does not introduce new functionality

**Why selected:** The implementation is correct; the gap is in test coverage and documentation.

### Option 2: Add Index Calls to Entity Service (Rejected)

**Pros:**
- Would fix the bug if index calls were missing

**Cons:**
- Index calls are already present -- adding duplicates would cause FTS5 insertion errors or duplicated entries

**Why rejected:** Investigation confirmed the calls already exist. Adding duplicate calls would be incorrect.

### Option 3: Move to Event-Driven Indexing (Rejected)

**Pros:**
- Decouples indexing from CRUD operations
- Could support additional index consumers in future

**Cons:**
- Introduces complexity (event bus, subscribers) for a simple synchronous operation
- SQLite transactions already guarantee consistency with direct calls
- Over-engineering for the current scale

**Why rejected:** The direct-call pattern is simple, reliable, and consistent with the model service pattern.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-03-01 | Accepted | Add regression tests and documentation | 6 months | 2026-09-01 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Architecture Team | 2026-03-01 |
| Accepted | Project Lead | 2026-03-01 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Extends | ADR-016 | Search Index Synchronisation | Covers incremental indexing gap not addressed in ADR-016 |
| Relates To | ADR-010 | Search Implementation Clarification | FTS5 is the current search technology |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-033-A | Entity Search Indexing Verification | Technical Specification | [specs/SPEC-033-A-Entity-Search-Indexing.md](specs/SPEC-033-A-Entity-Search-Indexing.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
