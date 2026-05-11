# SPEC-156-A: Scope `mcp_system_context` data passthrough

ADR: [ADR-156](../ADR-156-MCP-System-Context-Data-Passthrough.md)

## Database

### SQLite migration `backend/app/migrations/m050_rename_mcp_prompt_to_mcp_system_context.py`

Idempotent column rename on both `collections` and `sets`. PRAGMA-checks both sides of the rename so re-running on an already-renamed DB is a no-op.

```sql
ALTER TABLE collections RENAME COLUMN mcp_prompt TO mcp_system_context;
ALTER TABLE sets        RENAME COLUMN mcp_prompt TO mcp_system_context;
```

### Supabase migration `backend/app/migrations/supabase/m054_rename_mcp_prompt_to_mcp_system_context.sql`

Same rename via `information_schema.columns` guards. Idempotent.

## Backend

### Code rename (`mcp_prompt` → `mcp_system_context`)

| File | What changes |
|---|---|
| `backend/app/collections/models.py` | `CollectionUpdate.mcp_prompt` → `mcp_system_context`; same on `CollectionResponse` |
| `backend/app/collections/service.py` | `_COLLECTION_COLUMNS` SQL column ref; `_row_to_dict` key; `update_collection(...)` keyword arg |
| `backend/app/collections/router.py` | `update` endpoint passes `body.mcp_system_context` through |
| `backend/app/sets/models.py` | `SetUpdate.mcp_system_context`; `SetResponse.mcp_system_context` |
| `backend/app/sets/service.py` | `_SET_COLUMNS`; `_row_to_dict`; `update_set(...)` keyword |
| `backend/app/sets/router.py` | `update` endpoint passes through |

### Scope-prompt index

`backend/app/prompts/service.py:list_scope_prompts` now returns **named prompts only** (ADR-154 entries). The two scope-level SELECTs (`mcp_prompt` and previously `system_prompt`) are removed. Docstring rewritten.

### Ask Iris path

`backend/app/ai/scope_prompts.py` unchanged. Continues to use `system_prompt`. ADR-150 behaviour preserved.

## iris-client

`iris-client/src/iris_client/models/core.py`:
- `IrisSet`: `mcp_prompt` field renamed → `mcp_system_context`
- `Collection`: `mcp_prompt` field renamed → `mcp_system_context`

`IrisClient.list_scope_prompts()` is unchanged in shape; what it now returns from the server is named-prompt entries only.

## MCP server

### `mcp/src/iris_mcp/links.py:_STRIPPED_KEYS`

Unchanged: `("system_prompt",)`. The new `mcp_system_context` field is deliberately NOT in this list — it flows through every MCP tool response (`get_set`, `list_sets`, `get_collection`, `list_collections`, search results) as a regular data field.

### `mcp/src/iris_mcp/prompts.py`

No code changes — the MCP picker continues to consume `client.list_scope_prompts()`, which now returns only named-prompt entries.

## Web GUI

`/sets/[id]` and `/collections/[id]` edit pages: the "MCP prompt" textarea introduced in v5.10.0 (ADR-155) is:
- renamed to **"MCP system context"** (visible label)
- placeholder text rewritten: "Passed through as data on MCP get_set responses, so it lands as initial context when an MCP client is browsing this Set. Not applied in Iris AI."
- helper text rewritten: "Initial context for MCP clients (Claude Desktop / Claude Code) when retrieving this Set via the iris MCP server. Does NOT auto-apply in Iris AI and is NOT a slash-command prompt."

JS state variable: `mcpPrompt` → `mcpSystemContext`. PUT body field: `mcp_prompt` → `mcp_system_context`.

## Tests

| File | What |
|---|---|
| `backend/tests/test_migrations/test_mcp_system_context_rename.py` | 5 new cases — SQLite + Supabase rename, idempotency on both sides |
| `backend/tests/test_prompts/test_router.py` | Rewritten under ADR-156 contract: picker is named-prompts only, scope content does NOT appear in picker, anonymous read still works |
| `backend/tests/test_prompts/test_router_named_prompts_extension.py` | ADR-155 strict-split tests replaced with ADR-156 data-passthrough tests (mcp_system_context appears on get_set, not in picker; system_prompt still on backend response — strip is MCP-boundary) |
| `mcp/tests/test_links_passes_mcp_system_context.py` | 4 new cases — mcp_system_context survives `with_web_url`, `with_web_urls_list`, `with_web_urls_search` on Sets and Collections |
| `mcp/tests/test_links_strip_system_prompt.py` | Unchanged — ADR-151 strip still in force |
| `frontend/tests/unit/mcpSystemContext.test.ts` | Renamed from `mcpPrompt.test.ts`, field references updated |

## End-to-end verification

```bash
# 1. Apply Supabase m054 to the UAT DB:
./scripts/supabase-migrate.sh "postgresql://postgres:PASSWORD@db.<project>.supabase.co:5432/postgres"

# 2. On UAT, navigate to /sets/<doview-book-set-id>.
#    Confirm the "MCP prompt" textarea label is now "MCP system context".
#    Confirm any v5.10.0 content previously authored is preserved (column was renamed, not dropped).

# 3. In Claude Code with Iris MCP connected:
#    Run /mcp__iris__get_set with the DoView Book set_id.
#    Confirm the response includes `mcp_system_context` as a field with the authored content.
#    Confirm `system_prompt` is NOT in the response (ADR-151 strip still applies).

# 4. Open the MCP prompt picker — confirm:
#    - No `/iris:set:<uuid>` entry for any scope (ADR-156 removes the scope-level slash command).
#    - Named prompts authored on a scope still appear as `/iris:set:<uuid>:<name>`.

# 5. In Iris's web AI (Ask Iris on a question scoped to the DoView Book set):
#    Confirm system_prompt is still auto-applied (Iris-AI behaviour unchanged).
```

## Out of scope (deferred per ADR-156)

- Inheritance for `mcp_system_context`.
- Per-mode system_prompt split.
- Migration tooling to redistribute v5.10.0 `mcp_prompt` content.
