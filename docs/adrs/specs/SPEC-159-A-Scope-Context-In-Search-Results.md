# SPEC-159-A: Scope `mcp_system_context` in search results

ADR: [ADR-159](../ADR-159-Scope-Context-In-Search-Results.md)

## Database

**No schema changes.** `sets.mcp_system_context` and `collections.mcp_system_context` columns already exist (added in m050 / m054 per ADR-156).

## Backend

### `app/search/models.py:SearchResult`

Field added:

```python
mcp_system_context: str | None = None
# Only populated for set / collection hits (ADR-159).
```

### `app/search/service.py`

Four query branches updated. Each adds `s.mcp_system_context` (or `c.mcp_system_context`) to the SELECT and the result dict:

- SQLite, sets branch (`_search_sqlite` set hits)
- SQLite, collections branch (`_search_sqlite` collection hits)
- Postgres, sets branch (`_search_postgres` set hits)
- Postgres, collections branch (`_search_postgres` collection hits)

For non-scope hits (`element` / `diagram` / `package`), the field is unset on the dict and serialises to `null` (or is omitted, depending on Pydantic config).

## iris-client

`iris-client/src/iris_client/models/core.py:SearchResult` gains the same field. `_Permissive` base means pre-v5.14.0 server payloads (without the field) continue to validate, defaulting to `None`.

## MCP server

**No code changes.** The strip helper (`mcp/src/iris_mcp/links.py:_STRIPPED_KEYS`) is `("system_prompt",)`. `mcp_system_context` is intentionally pass-through per ADR-156, so it flows through search results as data the same way it does on `get_set` / `list_sets`.

## Frontend

**No changes.** The web UI doesn't render `mcp_system_context` in search-results UI. The frontend `SearchResult` typed wrapper (if any) tolerates the new field via `_Permissive`-equivalent extras-allowed config.

## Tests

| File | Cases | Layer |
|---|---|---|
| `backend/tests/test_search/test_mcp_system_context_in_results.py` | 4 — set hit populated; set hit null; collection hit populated; non-scope hit absent | backend |
| `iris-client/tests/test_search_mcp_system_context.py` | 4 — set with field; collection with field; legacy payload validates without field; non-scope hit | iris-client |

8 net new tests for v5.14.0.

Pre-existing 11 failures in `tests/test_search/test_rebuild.py` (fixture issue, not search-result-shape) are unrelated and continue to be the only acceptable failures alongside `test_no_extra_rls_tables` (issue 88 Phase 4 TODO).

## End-to-end verification

```bash
# 1. Configure mcp_system_context on a Set:
curl -X PUT http://localhost:8000/api/sets/<set-id> \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Outcomes Theory Book", "mcp_system_context": "Orient first."}'

# 2. Search for it:
curl "http://localhost:8000/api/search?q=outcomes"
# Expected: results[].mcp_system_context = "Orient first." for the set hit.

# 3. In Claude Desktop with Iris MCP connected, ask "open the outcomes theory book in iris".
#    Claude should call search, see the mcp_system_context on the hit,
#    and orient with the four-option menu before doing anything else.
```

## Out of scope (deferred)

- Surfacing on `list_packages` / `list_diagrams` results (sub-scope; not the orient channel).
- Dedicated `iris_get_scope_context(set_id)` MCP tool (same trigger problem).
- Search-results UI rendering of `mcp_system_context` (admin-facing; not user-facing).
