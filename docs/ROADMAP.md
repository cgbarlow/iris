# Iris Roadmap

This document tracks planned future enhancements for Iris that are out of current scope but recorded for future consideration.

---

## Future Enhancements

### Semantic Search (sentence-transformers + sqlite-vss)

**Description:** Replace or augment the current SQLite FTS5 keyword search with vector-based similarity search. This would enable natural-language queries that match on meaning rather than exact keywords — for example, searching for "authentication service" would find entities named "login component".

**Prerequisites:**
- sentence-transformers library (~2GB model download for embeddings)
- Embedding pipeline to compute and store vectors for all searchable entities and models
- sqlite-vss extension for vector similarity search in SQLite
- Query reformulation logic to convert user queries to embedding vectors
- Rank fusion to combine FTS5 lexical results with vector similarity results

**Scope:** Significant. The sentence-transformers model alone is approximately 2GB. An embedding indexing pipeline must be built to compute vectors on entity/model create and update. The sqlite-vss extension requires platform-specific native builds. Query latency increases due to embedding generation per search request.

**Status:** Planned, no target date. The current FTS5 implementation is production-ready and meets current user needs. Semantic search will be considered when FTS5 is demonstrably insufficient for user workflows.

**References:**
- [ADR-010: Search Implementation Clarification](adrs/ADR-010-Search-Implementation-Clarification.md)
- [SPEC-010-A: Search Roadmap](adrs/specs/SPEC-010-A-Search-Roadmap.md)
