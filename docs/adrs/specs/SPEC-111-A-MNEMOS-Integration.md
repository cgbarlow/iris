# SPEC-111-A: MNEMOS Integration

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-111-A |
| **ADR** | [ADR-111](../ADR-111-MNEMOS-Semantic-Retrieval.md) |
| **Status** | Draft |
| **Date** | 2026-03-29 |

## Overview

Integrate MNEMOS as an optional semantic retrieval layer in Iris's Ask AI pipeline, behind a `RetrievalPort` protocol abstraction, managed as an extension via the Extensions Framework (ADR-103).

## Architecture

```
User Question
    |
    v
router.py  ->  service.py  ->  RetrievalPort (protocol)
                                    |
                            +-------+-------+
                            |               |
                     DirectRetrieval   SemanticRetrieval
                     (existing logic)  (MNEMOS-powered)
                            |               |
                     context.py       mnemos/adapter.py
                     (current DB)     (mnemos_sdk client)
                            |               |
                            +-------+-------+
                                    |
                                    v
                            assembled context string
                                    |
                                    v
                              client.py (LLM call)
```

## RetrievalPort Protocol

```python
@runtime_checkable
class RetrievalPort(Protocol):
    async def retrieve_context(
        self,
        db: DatabasePort,
        question: str,
        set_ids: list[str],
        *,
        max_tokens: int = 8000,
        package_ids: list[str] | None = None,
    ) -> str:
        """Retrieve context for an AI question. Returns structured text."""
        ...
```

### DirectRetrieval

Wraps existing `build_set_context` / `build_multi_set_context` from `context.py`. Zero behavior change — this is the default when MNEMOS is not installed.

### SemanticRetrieval

Queries MNEMOS for relevant engrams, filtered by set neuro-tags and optional package tags. Formats results as structured text compatible with the existing LLM prompt format. Falls back to `DirectRetrieval` on any error.

## Extension Registration

MNEMOS follows the Scenia extension pattern (ADR-103):

- **Extension ID:** `mnemos`
- **Admin UI:** Extensions tab at `/admin/settings/extensions`
- **Config stored in `extensions.config` JSON:**
  ```json
  {
      "url": "http://localhost:8700",
      "timeout_ms": 5000,
      "max_results": 50
  }
  ```
- **Runtime gating:** `require_mnemos_enabled` FastAPI dependency (mirrors `require_scenia_enabled`)

## Engram Mapping

| Iris Entity | Engram Content | Neuro-Tags | Source URI |
|-------------|---------------|------------|------------|
| Element | `[{type}] {name}: {description} ({stereotypes})` | `element`, `set:{set_id}`, `type:{element_type}` | `iris://elements/{id}` |
| Relationship | `{source} --[{type}]--> {target}: {label}` | `relationship`, `set:{set_id}` | `iris://relationships/{id}` |
| Diagram | `[{type}] {name}: {description}` | `diagram`, `set:{set_id}`, `pkg:{package_id}` | `iris://diagrams/{id}` |

## Data Synchronization

- **Event-driven:** Async sync hooks after DB commits in element/relationship/diagram services (same pattern as FTS5 indexing)
- **Bulk reindex:** Admin endpoint `POST /api/mnemos/reindex`
- **Sync tracking:** `mnemos_sync_status` table tracks last-synced version per entity
- **Failure handling:** Log warning, continue — entity stale until next sync

## Graceful Degradation

1. Extension not installed/disabled → `DirectRetrieval` (zero change)
2. MNEMOS unreachable → `SemanticRetrieval` catches error, falls back to `DirectRetrieval`
3. Empty results → falls back to `DirectRetrieval`
4. Container crash → all requests auto-fallback

## Render Deployment

```yaml
  - type: web
    name: iris-mnemos
    runtime: docker
    plan: free
    region: singapore
    dockerfilePath: MNEMOS/Dockerfile
    dockerContext: MNEMOS
    disk:
      name: mnemos-data
      mountPath: /app/data
      sizeGB: 1
    envVars:
      - key: MNEMOS_TIERS
        value: chromadb
      - key: MNEMOS_QUANT_BITS
        value: "4"
      - key: MNEMOS_PORT
        value: "8700"
```

## Acceptance Criteria

1. `RetrievalPort` protocol exists with `DirectRetrieval` and `SemanticRetrieval` implementations.
2. `service.py` `ask_question` and `ask_multi_set_question` use `RetrievalPort` instead of calling `build_set_context` directly.
3. Existing tests pass unchanged after `DirectRetrieval` refactor.
4. MNEMOS appears in Extensions tab; install stores URL config in `extensions.config`.
5. When MNEMOS is enabled and reachable, Ask AI uses semantic retrieval for context.
6. When MNEMOS is unavailable, Ask AI falls back to direct retrieval transparently.
7. Bulk reindex endpoint populates MNEMOS from current Iris data.
8. Entity mutations trigger async MNEMOS sync.
