# SPEC-157-A: Response-format prompts + doview_analysis artefact

ADR: [ADR-157](../ADR-157-Response-Format-Prompts-and-DoView-Analysis-Artefact.md)

## Database

### SQLite migration `backend/app/migrations/m051_response_format_prompts.py`

Idempotent.

```sql
-- 1. Add `purpose` column to ai_creation_prompts.
ALTER TABLE ai_creation_prompts ADD COLUMN purpose TEXT NOT NULL DEFAULT 'creation_format';
UPDATE ai_creation_prompts SET purpose = 'creation_format' WHERE purpose IS NULL OR purpose = '';

-- 2. Register markdown notation + doview_analysis diagram_type + mapping.
-- (skipped gracefully via existence checks when registry tables aren't present)
INSERT OR IGNORE INTO notations (id, name, description, display_order)
    VALUES ('markdown', 'Markdown', '...', 5);
INSERT OR IGNORE INTO diagram_types (id, name, description, display_order)
    VALUES ('doview_analysis', 'DoView Analysis', '...', 10);
INSERT OR IGNORE INTO diagram_type_notations (diagram_type_id, notation_id, is_default)
    VALUES ('doview_analysis', 'markdown', 1);

-- 3. Seed three response_format prompt rows.
-- response-format-base-v1     (purpose=response_format, layer=base, notation=NULL, diagram_type=NULL)
-- response-format-doview-notation-v1   (purpose=response_format, layer=notation, notation=markdown)
-- response-format-doview-analysis-v1   (purpose=response_format, layer=diagram_type, diagram_type=doview_analysis)
```

Registry inserts wrapped in `sqlite_master` existence checks so the migration runs cleanly in test fixtures that have `ai_creation_prompts` but not the registry tables.

### Supabase migration `backend/app/migrations/supabase/m055_response_format_prompts.sql`

Same operations on Supabase (`ADD COLUMN IF NOT EXISTS`, `ON CONFLICT (id) DO NOTHING`). Bodies dollar-quoted.

## Backend

### Composer — `backend/app/ai/creation.py`

```python
async def _build_layered_prompt(
    db: aiosqlite.Connection, *, purpose: str, notation: str,
    diagram_type: str | None,
) -> tuple[str, int]:
    """Shared cascade composer. Returns (body, n_layers)."""

async def build_creation_system_prompt(db, notation, diagram_type=None) -> str:
    """Calls _build_layered_prompt with purpose='creation_format'.
    Unchanged from v5.8.x in terms of output for callers."""

async def build_response_system_prompt(db, notation, diagram_type=None) -> str:
    """Calls _build_layered_prompt with purpose='response_format'.
    New in v5.12.0 (ADR-157)."""
```

### Pydantic models — `backend/app/ai/models.py`

- `CreationPromptResponse` extended with `purpose: str = "creation_format"`.
- New `ResponsePromptComposed` (notation, diagram_type, body).
- New `ResponseFormatType` (notation, diagram_type, label, description).

### Endpoints — `backend/app/ai/router.py`

| Method | Path | Auth | Response |
|---|---|---|---|
| `GET` | `/api/ai/response-prompts/types` | Anonymous | `list[ResponseFormatType]` |
| `GET` | `/api/ai/response-prompts/composed?notation=&diagram_type=` | Anonymous | `ResponsePromptComposed` |
| `GET` | `/api/ai/creation-prompts?purpose=` | Admin (existing) | `list[CreationPromptResponse]` — `purpose` filter optional |
| `PUT` | `/api/ai/creation-prompts/{prompt_id}` | Admin (existing) | `CreationPromptResponse` — now round-trips `purpose` |

### Ask Iris pipeline — UNTOUCHED in v5.12.0

`build_response_system_prompt` is callable but not yet auto-injected by `Ask Iris` server-side composition. Deferred per ADR-157 "Out of scope". v5.12.0 path: explicit invocation by client model via MCP tool.

## iris-client

### Models — `iris-client/src/iris_client/models/core.py`

- `ResponseFormatType` (notation, diagram_type, label, description)
- `ResponsePromptComposed` (notation, diagram_type, body)

### Methods — `iris-client/src/iris_client/client.py`

```python
async def list_response_format_types(self) -> list[ResponseFormatType]
async def get_response_prompt(self, notation: str, diagram_type: str | None = None) -> ResponsePromptComposed
async def create_diagram(self, *, diagram_type, name, notation=None, data=None, set_id=None, parent_package_id=None, description=None) -> Diagram
```

`create_diagram` is the generic POST /api/diagrams wrapper — used by the save tool but available to other consumers too.

## MCP server

### Tools — `mcp/src/iris_mcp/tools.py`

| Tool | Purpose | Auth |
|---|---|---|
| `list_response_format_types` | Discover (notation, diagram_type) pairs with response_format prompts | Anonymous |
| `get_response_prompt(notation, diagram_type?)` | Fetch composed cascade body | Anonymous |
| `save_doview_analysis(set_id, name, content, parent_package_id?, description?)` | Persist a generated analysis as a `doview_analysis` diagram | Auth required (IRIS_TOKEN on server) |

### Auth posture

`save_doview_analysis` relies on the MCP server's `IRIS_TOKEN` env var (existing per-instance PAT). If the token is unset or invalid, the backend returns 401 and the tool surfaces the error.

## Frontend

No changes in v5.12.0. Admin Settings / AI GUI extension for `response_format` row editing is deferred per ADR-157 "Out of scope". Authoring works via the existing `PUT /api/ai/creation-prompts/{id}` endpoint with the new `purpose` field round-tripping correctly.

## Tests

| File | Cases | Layer | Notes |
|---|---|---|---|
| `backend/tests/test_migrations/test_response_format_prompts_schema.py` | 10 | migration | All passing — m051 SQLite + m055 Supabase + idempotency + content spot-checks |
| `backend/tests/test_ai/test_response_system_prompt.py` | 5 | composer | All passing — three-layer composition + isolation between creation_format and response_format |
| `backend/tests/test_ai/test_creation_service.py` | 11 | composer regression | All passing — existing creation composer unchanged after purpose-filter addition |
| `backend/tests/test_ai/test_creation_prompts_expanded.py` | 33 | seed regression | All passing — counts updated to assert 15 creation_format + 3 response_format rows |
| `iris-client/` (existing) | 30 | client | All passing |
| `mcp/` (existing) | 79 | MCP | All passing |

**Net new tests for v5.12.0**: 15 (10 migration + 5 composer). Test count adjustments: 1 (the row-count regression).

Pre-existing `test_no_extra_rls_tables` failure (issue 88 Phase 4 TODO, caps at m029) remains the only acceptable failure in the suite.

## Deployment / UAT setup

Beyond the migration, one manual step is required on each scope that should advertise the response_format workflow to MCP clients: paste a short pointer into the **MCP system context** field. Canonical content for the DoView Book Set is in [`docs/prompts/doview-book-mcp-system-context.md`](../../prompts/doview-book-mcp-system-context.md).

## End-to-end verification

```bash
# 1. Apply Supabase m055 to UAT DB.
./scripts/supabase-migrate.sh "postgresql://postgres:PASSWORD@db.<project>.supabase.co:5432/postgres"

# 2. Verify the response-format mechanism end-to-end via HTTP:
curl http://localhost:8000/api/ai/response-prompts/types
# → JSON list with one entry: {notation:"markdown", diagram_type:"doview_analysis", label:"DoView Analysis", description:"..."}

curl "http://localhost:8000/api/ai/response-prompts/composed?notation=markdown&diagram_type=doview_analysis"
# → JSON object with body containing the cascade (base + markdown notation + doview_analysis)

# 3. In Claude Desktop / Claude Code with Iris MCP connected, in conversation:
# - List the response-format types via mcp__iris__list_response_format_types
# - Fetch the composed prompt via mcp__iris__get_response_prompt
# - Verify the body contains Prompt-C-style rules (opening sentence, three sections, raw URLs)
# - If authenticated: save a generated analysis via mcp__iris__save_doview_analysis
#   and verify it appears as a new diagram of type doview_analysis under the chosen set.

# 4. Verify backwards compat — existing diagram creation still works:
# Create a new DoView outcomes_map via Ask Iris creation mode. The creation
# composer should still emit the full 15-row creation_format cascade, unchanged.
```

## Out of scope (deferred per ADR-157)

- Server-side auto-wiring of `build_response_system_prompt` into `Ask Iris`.
- `applicable_response_types` field on Set/Collection MCP responses.
- Admin Settings / AI GUI extension for response_format rows.
- Argument templating on prompt bodies.
- Auto-detection of when a response_format applies.
- Additional notations beyond `markdown / doview_analysis`.
- Creation_format companion seed for `doview_analysis`.
- Per-scope overrides of response_format (those remain `mcp_system_context`'s job).
