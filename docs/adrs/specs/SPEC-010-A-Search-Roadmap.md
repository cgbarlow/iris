# SPEC-010-A: Search Roadmap

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-010-A |
| **ADR Reference** | [ADR-010: Search Implementation Clarification](../ADR-010-Search-Implementation-Clarification.md) |
| **Date** | 2026-02-27 |
| **Status** | Active |

---

## Overview

This specification documents the current search implementation, what works today, and the future roadmap for semantic search capabilities in Iris.

---

## Current Implementation: SQLite FTS5

### Technology

| Aspect | Detail |
|--------|--------|
| **Engine** | SQLite FTS5 (Full-Text Search 5) |
| **Type** | Keyword-based full-text search with ranking |
| **Dependencies** | None beyond SQLite (FTS5 is a built-in extension) |
| **ML Components** | None |
| **Vector Storage** | None |

### What Works Today

| Feature | Endpoint | Description |
|---------|----------|-------------|
| Entity search | `GET /api/search?q=...` | Full-text keyword search across entity names, descriptions, and metadata |
| Model search | `GET /api/search?q=...` | Full-text keyword search across model names and descriptions |

### FTS5 Capabilities

- Tokenised keyword matching with prefix search
- BM25 relevance ranking
- Boolean operators (AND, OR, NOT)
- Phrase matching with quoted strings
- Column-specific filtering
- Highlight and snippet generation

### Limitations of FTS5

- No semantic understanding — "authentication service" does not match "login component"
- No synonym awareness — "DB" does not match "database"
- No natural-language query interpretation
- Ranking is based on term frequency, not meaning

---

## Future Roadmap: Semantic Search

### Goal

Replace or augment FTS5 keyword search with vector-based similarity search using sentence-transformers embeddings and sqlite-vss, enabling natural-language queries that match on meaning rather than exact keywords.

### Components Required

| Component | Purpose | Impact |
|-----------|---------|--------|
| **sentence-transformers** | Generate vector embeddings from entity/model text | ~2GB model download, Python dependency |
| **Embedding pipeline** | Compute and store embeddings for all searchable content | Batch indexing on startup, incremental on create/update |
| **sqlite-vss** | SQLite extension for vector similarity search | Native extension, platform-specific builds |
| **Query reformulation** | Convert user queries to embeddings for similarity matching | Additional latency per search request |
| **Hybrid search** | Combine FTS5 keyword results with vector similarity results | Ranking fusion logic |

### Architecture

```
User query
    |
    v
[Embedding model] --> query vector
    |
    v
[sqlite-vss] --> similarity results (semantic)
    |
[FTS5] ---------> keyword results (lexical)
    |
    v
[Rank fusion] --> combined, ranked results
```

### Prerequisites

Before implementing semantic search, the following conditions should be met:

1. **FTS5 search is demonstrably insufficient** — users report that keyword search does not meet their needs for finding entities and models
2. **Infrastructure budget allows ~2GB model** — the sentence-transformers model must be downloaded and stored; this is appropriate for server deployments but may be heavy for local development
3. **Embedding maintenance is scoped** — a plan exists for when to re-embed content (on entity create/update, on model create/update, batch re-index on schema changes)
4. **sqlite-vss is stable** — the extension must be available and stable for the target deployment platforms
5. **Scope approval** — semantic search is a significant feature that must be explicitly approved per principle 6 (scope discipline)

### Scope Estimate

| Aspect | Estimate |
|--------|----------|
| **Model size** | ~2GB (e.g., all-MiniLM-L6-v2 at ~80MB, or larger models up to 2GB) |
| **New dependencies** | sentence-transformers, torch (or onnxruntime), sqlite-vss |
| **Embedding pipeline** | Batch indexing + incremental updates on entity/model mutations |
| **Query path changes** | Embedding generation per query + vector search + rank fusion |
| **Testing** | Embedding quality validation, search relevance benchmarks, performance testing |

### Status

| Field | Value |
|-------|-------|
| **Status** | Planned |
| **Target Date** | No target date |
| **Priority** | Low — FTS5 meets current needs |
| **Tracking** | See `docs/ROADMAP.md` |

---

## Migration Path

When semantic search is implemented:

1. FTS5 remains as the lexical search component (not removed)
2. Vector search is added as a parallel search path
3. Results from both paths are combined using rank fusion
4. The API contract (`GET /api/search?q=...`) remains unchanged — the improvement is transparent to callers
5. An optional `mode` parameter may be added to allow callers to request keyword-only or semantic-only results

---

*This specification implements [ADR-010](../ADR-010-Search-Implementation-Clarification.md).*
