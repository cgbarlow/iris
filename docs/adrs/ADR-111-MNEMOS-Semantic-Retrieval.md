# ADR-111: MNEMOS Semantic Retrieval Integration

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-111 |
| **Initiative** | MNEMOS Semantic Retrieval for Ask AI |
| **Proposed By** | Engineering |
| **Date** | 2026-03-29 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris "Ask AI" feature, which builds LLM context by querying all elements, relationships, and diagrams from the database and serializing them to structured text with proportional truncation,

**facing** the challenge that naively dumping all entities wastes token budget on irrelevant items, multi-set queries divide the budget equally across sets (starving each one), keyword-only FTS5/tsvector search misses semantically related entities, and there is no conversation memory across sessions,

**we decided for** integrating MNEMOS as an optional semantic retrieval layer behind a `RetrievalPort` protocol abstraction, registered as an Iris extension via the ADR-103 Extensions Framework, with automatic fallback to the existing direct-query approach when MNEMOS is unavailable or not configured,

**and neglected** replacing `context.py` entirely with MNEMOS (makes it a hard dependency — Ask AI breaks when MNEMOS is down), adding pgvector/sqlite-vec directly to the Iris database (significant engineering to replicate what MNEMOS provides), using a hosted vector database like Pinecone (mandatory external dependency, breaks self-hosted model), and using only smarter FTS heuristics without embeddings (does not solve semantic gap),

**to achieve** question-aware semantic retrieval that returns only relevant entities ranked by similarity, cross-set semantic search without per-set budget starvation, graceful degradation that preserves existing behavior when MNEMOS is unavailable, and a clean extension-based opt-in model for both self-hosted and cloud deployments,

**accepting that** this adds a second Docker container (~350MB) for users who enable it, requires data synchronization between the Iris database and MNEMOS engram index, and introduces latency (~50-200ms) for the MNEMOS network hop (negligible relative to 2-30s LLM calls).

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| RetrievalPort Abstraction | Protocol-based retrieval strategy with Direct and Semantic implementations | [SPEC-111-A](./specs/SPEC-111-A-MNEMOS-Integration.md) |
| MNEMOS Extension | Admin-managed extension via Extensions tab, following Scenia pattern | [SPEC-111-A](./specs/SPEC-111-A-MNEMOS-Integration.md) |
| Engram Mapping | Iris elements, relationships, diagrams mapped to MNEMOS engrams | [SPEC-111-A](./specs/SPEC-111-A-MNEMOS-Integration.md) |
| Data Synchronization | Event-driven sync with bulk reindex and catch-up mechanisms | [SPEC-111-A](./specs/SPEC-111-A-MNEMOS-Integration.md) |
| Graceful Degradation | Automatic fallback to direct retrieval on MNEMOS failure | [SPEC-111-A](./specs/SPEC-111-A-MNEMOS-Integration.md) |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Extends | ADR-093 | AI Model Management | Adds semantic retrieval to the existing AI Q&A pipeline |
| Extends | ADR-102 | Collections | Improves multi-set context quality |
| Extends | ADR-103 | Extensions Framework | MNEMOS registered as an extension |
| Relates To | ADR-109 | Package-Level AI Context | Package filtering works with both retrieval strategies |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-111-A | MNEMOS Integration | Technical Specification | [specs/SPEC-111-A-MNEMOS-Integration.md](./specs/SPEC-111-A-MNEMOS-Integration.md) |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-03-29 |
| Approved | Engineering | 2026-03-29 |

## Amendment 2026-05-06 — v5.5.0: MNEMOSv2 + auto-clone (issue #48)

`backend/app/mnemos/setup.py` previously expected operators to
manually clone the MNEMOS repo as a sibling directory. v5.5.0 adds
`clone_or_update_repo(source_url, branch?)` so the install + upgrade
flow can pull / update from a configured source URL automatically.

The default source URL is now
`https://github.com/ro0TuX777/MNEMOSv2.git` (the v2 fork superseding
the original repo). Override at deploy time via
`IRIS_MNEMOS_REPO_URL` and `IRIS_MNEMOS_REPO_BRANCH`. The helper
handles both fresh clone (creates the parent dir and runs `git
clone --depth 1 --branch <branch>`) and update (`git fetch && git
reset --hard origin/<branch>`).

Pairs with the new daily extension scanner (ADR-146) and the new
POST `/api/extensions/{id}/upgrade` endpoint, which calls this helper
between the existing stop_container / start_container lifecycle.
