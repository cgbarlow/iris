# ADR-016: Search Index Synchronisation

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-016 |
| **Initiative** | Search Index Synchronisation |
| **Proposed By** | Architecture Team |
| **Date** | 2026-02-28 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris search subsystem, where FTS5 virtual tables (entities_fts, models_fts) are created by migration m005_search.py but never populated from existing entity and model data, and where rollback operations on entities do not update the FTS index to reflect the rolled-back name and description,

**facing** the problem that search returns zero results for any entities or models that existed before FTS5 indexing was added, that any data inserted directly into the database (e.g., during migration or bulk import) is invisible to search, and that rolling back an entity to a previous version leaves stale data in the search index,

**we decided for** adding a `rebuild_search_index()` function that clears and repopulates both FTS5 tables from current entity and model data, calling it on every application startup after migrations, and fixing the `rollback_entity()` function to re-index the entity after rollback,

**and neglected** using FTS5 content-sync tables (which would require schema changes to the existing FTS5 tables and add complexity), and relying solely on incremental indexing during CRUD operations (which does not solve the initial population problem for pre-existing data),

**to achieve** immediate search availability for all existing entities and models on startup, correct search results after entity rollback, and idempotent index rebuilding that is safe to run on every startup without data duplication,

**accepting that** rebuilding the full index on every startup adds a small amount of startup time proportional to the number of entities and models, and that the rebuild approach is a simple brute-force solution rather than an incremental sync mechanism.

---

## Options Considered

### Option 1: Startup Rebuild with Rollback Fix (Selected)

**Pros:**
- Simple and reliable -- full rebuild guarantees consistency
- Idempotent -- safe to run on every startup
- Fixes both the initial population gap and the rollback indexing gap
- No schema changes to existing FTS5 tables required

**Cons:**
- Rebuilds the entire index on every startup, even if nothing changed
- Startup time grows linearly with data volume (acceptable for expected scale)

### Option 2: FTS5 Content-Sync Tables (Rejected)

**Pros:**
- Automatic synchronisation between source tables and FTS index
- No explicit rebuild needed

**Cons:**
- Requires recreating FTS5 tables with content= and content_rowid= parameters
- Adds migration complexity
- Still requires triggers or explicit rebuild for initial population
- Content-sync tables have limitations with DELETE operations

**Why rejected:** Disproportionate complexity for the scale of data Iris handles. A simple rebuild is clearer and more maintainable.

### Option 3: Incremental CRUD-Only Indexing (Rejected)

**Pros:**
- No startup cost
- Index stays in sync during normal CRUD operations

**Cons:**
- Does not solve the initial population problem
- Does not fix data that was inserted before FTS5 was added
- Requires every code path that mutates entities/models to also update FTS

**Why rejected:** Does not address the root cause -- FTS tables are empty after creation.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-28 | Accepted | Implement rebuild and rollback fix | 6 months | 2026-08-28 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Architecture Team | 2026-02-28 |
| Accepted | Project Lead | 2026-02-28 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Relates To | ADR-010 | Search Implementation Clarification | FTS5 is the current search technology |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-016-A | Search Index Sync Specification | Technical Specification | [specs/SPEC-016-A-Search-Index-Sync.md](specs/SPEC-016-A-Search-Index-Sync.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
