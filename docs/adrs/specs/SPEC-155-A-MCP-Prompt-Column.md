# SPEC-155-A: Strict-split scope prompts — `mcp_prompt` column

ADR: [ADR-155](../ADR-155-Strict-Split-Iris-AI-vs-MCP-Scope-Prompts.md)

## Database

### SQLite migration `backend/app/migrations/m049_mcp_prompt_column.py`

Idempotent. Mirrors `m047_scope_system_prompts.py` style: PRAGMA-check existence before ALTER.

```sql
ALTER TABLE collections ADD COLUMN mcp_prompt TEXT;
ALTER TABLE sets ADD COLUMN mcp_prompt TEXT;
```

### Supabase migration `backend/app/migrations/supabase/m053_mcp_prompt_and_prompts_timestamps.sql`

Two changes in one file:

1. `ALTER TABLE collections / sets ADD COLUMN IF NOT EXISTS mcp_prompt TEXT` (mirrors the SQLite addition).

2. **Hotfix for v5.9.0 prompts table.** `prompts.created_at` and `prompts.updated_at` columns are converted from `text` to `timestamptz`. The Supabase adapter (`backend/app/db/adapter.py:_convert_params`) auto-converts ISO datetime strings to native `datetime` before handing them to asyncpg; asyncpg then rejects `datetime` going into a `text` column, producing `DataError: invalid input for query argument $7: datetime.datetime(...)` on every named-prompt insert. Every other Iris table uses `timestamptz`; the prompts table now matches.

Guarded with `information_schema.columns` checks so re-running on an already-fixed DB is a no-op.

## Backend

### Pydantic models

`backend/app/collections/models.py`:
- `CollectionUpdate.mcp_prompt: str | None = None`
- `CollectionResponse.mcp_prompt: str | None = None`

`backend/app/sets/models.py`:
- `SetUpdate.mcp_prompt: str | None = None`
- `SetResponse.mcp_prompt: str | None = None`

### Service layer

`backend/app/collections/service.py`:
- `_COLLECTION_COLUMNS` adds `c.mcp_prompt` (column index 11).
- `_row_to_dict` reads `row[11]` for the `mcp_prompt` key.
- `update_collection(...)` accepts new keyword `mcp_prompt: str | None`, includes it in both UPDATE branches.

`backend/app/sets/service.py`:
- `_SET_COLUMNS` adds `s.mcp_prompt` (column index 13).
- `_row_to_dict` reads `row[13]` for the `mcp_prompt` key.
- `update_set(...)` accepts new keyword `mcp_prompt: str | None`, includes it in both UPDATE branches.

### Scope-prompt index

`backend/app/prompts/service.py:list_scope_prompts` switches its two scope-level SELECTs from `system_prompt` to `mcp_prompt`. Filtering rule unchanged: `IS NOT NULL` + non-whitespace `body.strip()`.

Entry shape is unchanged. `entry_kind` literal stays `"system_prompt"` to preserve backwards-compat with the iris-client / MCP layer discriminator (rename would be a breaking change to every consumer; the literal is now slightly misnamed but the behaviour is correct under ADR-155).

### Ask Iris path (UNCHANGED)

`backend/app/ai/scope_prompts.py:build_scope_prompts` continues to read `system_prompt` only. Composition order, dedup, and inheritance rules from ADR-150 unchanged.

### Routers

`backend/app/collections/router.py:update` passes `body.mcp_prompt` through to the service.

`backend/app/sets/router.py:update` passes `body.mcp_prompt` through to the service.

## iris-client

`iris-client/src/iris_client/models/core.py`:
- `IrisSet` gains explicit `system_prompt: str | None = None` and `mcp_prompt: str | None = None`.
- `Collection` gains the same two fields.

(The base class is `_Permissive`, so the fields would flow through implicitly without these declarations. Making them explicit is for static type access in client code.)

`IrisClient.list_scope_prompts()` is unchanged — its `ScopePromptIndexEntry` model already returns `body` from whichever column the server picks.

## MCP server

**No changes.** `mcp/src/iris_mcp/prompts.py` consumes the scope-index response and reflects whatever bodies the server sends. The column-routing change is server-side only.

## Frontend

### `/sets/[id]` and `/collections/[id]` edit pages

Add a second `<textarea id="..-edit-mcp-prompt" bind:value={mcpPrompt}>` below the existing "System prompt" textarea. Same maxlength (20000), same monospace styling, same DOMPurify sanitisation on save. PUT body now carries both `system_prompt` and `mcp_prompt`.

Helper hint copy on each:
- System prompt: "Used by Iris's internal AI flows (discuss / creation). Not sent through MCP."
- MCP prompt: "The opposite of System prompt. Sent to MCP clients (Claude Desktop / Claude Code) via the prompt picker. Does NOT auto-apply in Iris AI."

## Tests

| File | New cases | Layer |
|---|---|---|
| `backend/tests/test_migrations/test_mcp_prompt_schema.py` | 5 (SQLite m049 + Supabase m053 + idempotency + timestamptz fix) | migration |
| `backend/tests/test_prompts/test_router_named_prompts_extension.py` | 3 new strict-split cases (system_prompt alone → no MCP entry; mcp_prompt alone → MCP entry appears; both populated → MCP body is mcp_prompt) | backend |
| `frontend/tests/unit/mcpPrompt.test.ts` | 4 (PUT body shape, sanitisation, independence) | frontend |

Updated v5.8.x scope-index tests to populate `mcp_prompt` (not `system_prompt`) when asserting MCP picker visibility, matching the new column-routing semantics under ADR-155.

## End-to-end verification

```bash
# 1. Apply Supabase m053 to the UAT DB:
./scripts/supabase-migrate.sh "postgresql://postgres:PASSWORD@db.<project>.supabase.co:5432/postgres"

# 2. On UAT, navigate to /sets/<doview-book-set-id>.
#    Confirm the existing "System prompt" textarea retains its content.
#    Confirm a new "MCP prompt" textarea is empty.
#    Populate the MCP prompt and save.

# 3. In Claude Code with Iris MCP connected, run /mcp__iris__set:<uuid>.
#    Confirm the loaded body matches the new mcp_prompt content (NOT system_prompt).

# 4. In Iris's web AI (Ask Iris on a question scoped to that Set):
#    Confirm system_prompt is still auto-applied (unchanged Iris-AI behaviour).
```

## Out of scope (deferred per ADR-155)

- Inheritance for `mcp_prompt` (picker disambiguates per-scope).
- Per-mode `system_prompt` (discuss vs. creation).
- One-time content migration tool to copy `system_prompt` → `mcp_prompt`.
