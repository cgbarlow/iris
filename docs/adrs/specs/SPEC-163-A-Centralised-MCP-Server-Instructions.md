# SPEC-163-A: Centralised, admin-editable MCP server instructions

ADR: [ADR-163](../ADR-163-Centralised-MCP-Server-Instructions.md)

## Database

**No schema changes.** One singleton row added to `ai_creation_prompts` with the new `purpose='mcp_server_instructions'` discriminator value.

### SQLite seed migration `m053_mcp_server_instructions_seed.py`

```python
MIGRATION_ID = "m053_mcp_server_instructions_seed"

_SEED_BODY = """<canonical seeded body — see docs/prompts/mcp-server-instructions.md>""".strip()

async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        "INSERT OR IGNORE INTO ai_creation_prompts ("
        "  id, name, description, purpose, layer,"
        "  notation, diagram_type, prompt_text, display_order, is_active"
        ") VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, 0, 1)",
        (
            "mcp-server-instructions-v1",
            "MCP Server Instructions",
            "Universal orient-first protocol + discovery catalogue surfaced by iris-mcp via the MCP server `instructions` field (ADR-163, v5.18.0). One singleton row at layer=base.",
            "mcp_server_instructions",
            "base",
            _SEED_BODY,
        ),
    )
    await db.commit()
```

### Supabase mirror `m057_mcp_server_instructions_seed.sql`

```sql
INSERT INTO public.ai_creation_prompts (
    id, name, description, purpose, layer,
    notation, diagram_type, prompt_text, display_order, is_active
) VALUES (
    'mcp-server-instructions-v1',
    'MCP Server Instructions',
    'Universal orient-first protocol + discovery catalogue surfaced by iris-mcp via the MCP server `instructions` field (ADR-163, v5.18.0). One singleton row at layer=base.',
    'mcp_server_instructions',
    'base',
    NULL,
    NULL,
    $body$<canonical seeded body>$body$,
    0,
    TRUE
)
ON CONFLICT (id) DO NOTHING;
```

Idempotent on both backends.

## Backend

### `backend/app/ai/models.py`

Extend `CreationPromptCreate.purpose`:

```python
purpose: Literal[
    "creation_format",
    "response_format",
    "mcp_server_instructions",
] = "creation_format"
```

Add response model `ServerInstructionsResponse`:

```python
class ServerInstructionsResponse(BaseModel):
    body: str
```

### `backend/app/ai/router.py`

Extend `_VALID_PURPOSES`:

```python
_VALID_PURPOSES = ("response_format", "creation_format", "mcp_server_instructions")
```

Add endpoint:

```python
@router.get("/server-instructions", response_model=ServerInstructionsResponse)
async def get_mcp_server_instructions(
    request: Request,
    _current_user: dict[str, Any] | None = Depends(get_optional_user),
) -> ServerInstructionsResponse:
    """Return the singleton mcp_server_instructions row body (ADR-163,
    v5.18.0). Anonymous-readable; iris-mcp fetches at startup to
    populate the MCP server `instructions` field."""
    db = request.app.state.db_manager.main_db
    cursor = await db.execute(
        "SELECT prompt_text FROM ai_creation_prompts"
        " WHERE purpose = 'mcp_server_instructions'"
        "   AND is_active = 1"
        " ORDER BY display_order ASC, id ASC LIMIT 1",
    )
    row = await cursor.fetchone()
    if row is None:
        return ServerInstructionsResponse(body="")
    return ServerInstructionsResponse(body=row[0])
```

### Backend tests

`backend/tests/test_ai/test_server_instructions_endpoint.py`:

- 200 OK returns the seeded body.
- Empty body when no active row of that purpose exists.
- Anonymous-readable (no Authorization header required).
- Returns the most-recently-seeded body when multiple rows exist (display_order then id).

`backend/tests/test_migrations/test_mcp_server_instructions_seed.py`:

- m053 inserts a row with the expected id, purpose, layer, prompt_text non-empty.
- m057 mirrors with the same constraints (static-parser test on the SQL).

## iris-mcp

### `mcp/src/iris_mcp/server_instructions.py`

```python
"""Fetch the MCP server `instructions` text at startup (ADR-163,
v5.18.0). Falls back to a hardcoded baseline if the backend is
unreachable so the MCP server stays functional in degraded states."""

from __future__ import annotations

import httpx

_FALLBACK_INSTRUCTIONS = """<copy of the seeded body>""".strip()


async def fetch_server_instructions(iris_url: str) -> str:
    try:
        async with httpx.AsyncClient(base_url=iris_url, timeout=5.0) as c:
            response = await c.get("/api/ai/server-instructions")
            response.raise_for_status()
            body = response.json().get("body") or ""
            return body if body.strip() else _FALLBACK_INSTRUCTIONS
    except (httpx.HTTPError, ValueError):
        return _FALLBACK_INSTRUCTIONS
```

### `mcp/src/iris_mcp/server.py:build_server()`

```python
def build_server(
    client: IrisClient,
    *,
    instructions: str | None = None,
) -> Server:
    server: Server = Server(
        "iris-mcp",
        version=_package_version(),
        instructions=instructions,  # ADR-163, v5.18.0
        website_url="https://github.com/cgbarlow/iris",
        icons=[iris_icon()],
    )
    ...
```

### `mcp/src/iris_mcp/__main__.py:run()`

```python
async def run() -> None:
    config = load()
    token, source = _resolve_token(config.token, config.url)
    print(f"iris-mcp: using {source}", file=sys.stderr)
    instructions = await fetch_server_instructions(config.url)
    async with IrisClient(url=config.url, token=token) as client:
        server = build_server(client, instructions=instructions)
        ...
```

### MCP tests

`mcp/tests/test_server_instructions.py`:

- Happy fetch returns the body.
- Network error (`httpx.RequestError`) falls back.
- HTTP error (404, 500) falls back.
- 200 OK with empty body falls back to the hardcoded baseline.
- Bad JSON / non-JSON response falls back.

`mcp/tests/test_server_instructions_wiring.py`:

- `build_server(client, instructions="hello")` produces a `Server` whose `instructions` attribute is `"hello"`.
- `build_server(client)` (no kwarg) produces a `Server` with `instructions=None`.

## Frontend

### `frontend/src/routes/admin/settings/ai/+page.svelte`

Extend `PURPOSES`:

```ts
const PURPOSES = [
    'creation_format',
    'response_format',
    'mcp_server_instructions',
] as const;
```

Extend `appliesToLabel()` to special-case the new purpose:

```ts
if (p.purpose === 'mcp_server_instructions') return 'Server-wide (MCP instructions)';
```

(Branch checked before the existing `layer` branches so it wins for `layer=base, purpose=mcp_server_instructions`.)

### Frontend test

`frontend/tests/unit/adminPromptPurposeEnum.test.ts`:

- `PURPOSES` includes `mcp_server_instructions`.
- `appliesToLabel({ purpose: 'mcp_server_instructions', layer: 'base', notation: null, diagram_type: null })` returns "Server-wide (MCP instructions)".

## Canonical doc + per-scope trimming

### New `docs/prompts/mcp-server-instructions.md`

Canonical paste-ready content. Mirrors the seeded body. Provides admins a place to copy from if they edit and need to revert. Same pattern as `docs/prompts/doview-book-mcp-system-context.md`.

### Trim `docs/prompts/doview-book-mcp-system-context.md`

Strip ORIENT-FIRST wrapper (now in server instructions) and DISCOVERABILITY catalogue (also moved). Keep: one-sentence description, structural-overview call name, the menu options verbatim. ~12 lines (was ~30 in v5.17.0).

## End-to-end verification

After UAT deploy:

1. Visit `/admin/settings/ai`. Filter `purpose=mcp_server_instructions`. One row appears with the seeded body. Click edit, change a single word, save.
2. Restart Claude Desktop. The new session sees the updated instructions (visible indirectly through Claude's orient behaviour).
3. Stop the backend / point iris-mcp at a dead URL. Restart Claude Desktop. iris-mcp still starts and uses the hardcoded fallback.
4. Open the Outcomes Theory Book set fresh in Claude. Orient-first protocol fires (describe scope, call structural overview, present menu verbatim) even though the scope context no longer contains the protocol — proving the centralisation.
5. Author a fresh test set with a minimal `mcp_system_context` (just description + structural call + 2-option menu). Open it via Claude. The protocol still fires. Centralisation works for any scope.

## Manual UAT step

Apply m057 Supabase migration via `./scripts/supabase-migrate.sh`. Then paste the trimmed `docs/prompts/doview-book-mcp-system-context.md` content into the Outcomes Theory Book set's `mcp_system_context` field.

## Test counts target

- Backend: ~6 (endpoint happy / empty row / anonymous / multiple rows / Pydantic literal accept / migration static-parser)
- MCP: ~7 (5 fetch cases + 2 wiring cases)
- Frontend: ~2 (PURPOSES + appliesToLabel)
- iris-client: 0
- **Total**: ~15 new tests for v5.18.0
- **Combined suite**: ~548+ tests passing

## Out of scope (deferred)

- Deduplicating the three text copies (seed body / hardcoded fallback / canonical doc) — v6.0.0.
- Instructions versioning — no current need.
- Cascading multiple instructions rows — singleton is sufficient.
- Renaming `ai_creation_prompts` table — cosmetic; v6.0.0.
- Admin UI authoring-metadata for the singleton — UX polish; v5.19+.
