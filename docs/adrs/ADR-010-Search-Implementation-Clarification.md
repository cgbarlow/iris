# ADR-010: Search Implementation Clarification

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-010 |
| **Initiative** | Iris Documentation Accuracy — Search |
| **Proposed By** | Architecture Team |
| **Date** | 2026-02-27 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris search implementation, where the README and north-star tech stack claim sentence-transformers / sqlite-vss semantic search, but the actual implementation uses SQLite FTS5 full-text keyword search with no ML dependencies, embeddings, or vector storage present in the codebase,

**facing** a documentation-to-implementation mismatch that misleads contributors and stakeholders about actual capabilities, creates false expectations about dependencies and infrastructure requirements, and obscures the fact that FTS5 keyword search is production-ready and working,

**we decided for** acknowledging that the current search implementation is SQLite FTS5 full-text keyword search, correcting documentation that incorrectly claims semantic search capabilities, and deferring sentence-transformers / sqlite-vss semantic search to the roadmap as a future enhancement,

**and neglected** implementing semantic search now (which would require sentence-transformers at approximately 2GB model size, an embedding pipeline for all entities and models, sqlite-vss extension installation and management, and query reformulation logic — significant scope that violates principle 6: scope discipline), and removing search entirely (FTS5 works well for keyword search and meets current user needs),

**to achieve** documentation that accurately reflects the implemented system, clear expectations for contributors and stakeholders about current capabilities, a concrete roadmap item for semantic search when the project is ready to take on that scope, and maintained trust in project documentation as a reliable source of truth,

**accepting that** FTS5 keyword search is less capable than semantic search for natural-language queries, that updating documentation to reflect reality may surface other documentation-implementation mismatches, and that the semantic search roadmap item has no target date and may be deprioritised indefinitely.

---

## Current Implementation

| Aspect | Value |
|--------|-------|
| **Search Technology** | SQLite FTS5 (Full-Text Search) |
| **Search Type** | Keyword-based full-text search |
| **Endpoint** | `GET /api/search?q=...` |
| **Scope** | Entity and model search |
| **ML Dependencies** | None |
| **Vector Storage** | None |

FTS5 is built into SQLite, requires no additional dependencies, and provides production-quality keyword search with ranking.

---

## Documentation Corrections

| Document | Before | After |
|----------|--------|-------|
| `README.md` line 26 | "Semantic search with sentence-transformers embeddings" | "Full-text search with SQLite FTS5 (semantic search planned — see docs/ROADMAP.md)" |
| `docs/north-star.md` Tech Stack table, Search row | "sqlite-vss / sentence-transformers" | "SQLite FTS5 (semantic search planned — see ROADMAP)" |

---

## Options Considered

### Option 1: Correct Documentation, Defer Semantic Search (Selected)

**Pros:**
- Documentation accurately reflects implementation
- No new dependencies or scope
- FTS5 is production-ready and working
- Semantic search remains a roadmap item when the project is ready
- Follows principle 6 (scope discipline)

**Cons:**
- Acknowledges a gap between aspiration and current capability

### Option 2: Implement Semantic Search Now (Rejected)

**Pros:**
- Would make documentation accurate by implementing the claimed feature
- Better search quality for natural-language queries

**Cons:**
- Significant scope: sentence-transformers (~2GB model download), embedding pipeline for all searchable content, sqlite-vss extension, query reformulation logic
- Violates scope discipline — search works today with FTS5
- Adds heavyweight ML dependencies to a lightweight SQLite-based application
- Embedding pipeline requires ongoing maintenance (re-embed on entity changes)

**Why rejected:** Disproportionate effort to make documentation accurate. Correcting the documentation is the right fix.

### Option 3: Remove Search Entirely (Rejected)

**Pros:**
- Eliminates the documentation mismatch entirely

**Cons:**
- FTS5 search works well and serves user needs
- Removing working functionality is wasteful
- Search is listed as a success criterion in the north star

**Why rejected:** FTS5 works. There is no reason to remove it.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-27 | Approved | Correct documentation, create roadmap entry | 6 months | 2026-08-27 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Architecture Team | 2026-02-27 |
| Approved | Project Lead | 2026-02-27 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Relates To | ADR-003 | Architectural Vision | Search is part of The Engine layer |
| Relates To | ADR-004 | Backend Language and Framework | FTS5 search implemented in FastAPI |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-010-A | Search Roadmap | Technical Specification | [specs/SPEC-010-A-Search-Roadmap.md](specs/SPEC-010-A-Search-Roadmap.md) |
| DOC-001 | Iris Roadmap | Documentation | [../../ROADMAP.md](../../ROADMAP.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
