# SPEC-154-A: Multiple named prompts per scope

ADR: [ADR-154](../ADR-154-Multiple-Named-Prompts-per-Scope.md)

## Database

### SQLite migration `backend/app/migrations/m048_named_prompts.py`

Idempotent. Mirrors `m047_scope_system_prompts.py` style: pre-check
existence, run `CREATE TABLE IF NOT EXISTS`, log a single line.

```sql
CREATE TABLE IF NOT EXISTS prompts (
  id           TEXT PRIMARY KEY,
  scope_type   TEXT NOT NULL CHECK (scope_type IN ('collection','set')),
  scope_id     TEXT NOT NULL,
  name         TEXT NOT NULL,
  description  TEXT NOT NULL,
  body         TEXT NOT NULL,
  created_at   TEXT NOT NULL,
  updated_at   TEXT NOT NULL,
  created_by   TEXT,
  UNIQUE (scope_type, scope_id, name)
);
CREATE INDEX IF NOT EXISTS idx_prompts_scope ON prompts(scope_type, scope_id);
```

No FK constraint to `collections` / `sets` (Iris's existing pattern is
soft-delete + application-level integrity, e.g. `m047`). Soft-delete
of a scope leaves orphan named prompts — same posture as today's
`system_prompt` column.

### Supabase migration `backend/app/migrations/supabase/m052_named_prompts.sql`

Same shape with Supabase idiom (`IF NOT EXISTS` guards), plus RLS
policies aligned with ADR-095:

```sql
CREATE TABLE IF NOT EXISTS public.prompts (
  id           text PRIMARY KEY,
  scope_type   text NOT NULL CHECK (scope_type IN ('collection','set')),
  scope_id     text NOT NULL,
  name         text NOT NULL,
  description  text NOT NULL,
  body         text NOT NULL,
  created_at   text NOT NULL,
  updated_at   text NOT NULL,
  created_by   text,
  UNIQUE (scope_type, scope_id, name)
);
CREATE INDEX IF NOT EXISTS idx_prompts_scope ON public.prompts(scope_type, scope_id);

ALTER TABLE public.prompts ENABLE ROW LEVEL SECURITY;

CREATE POLICY prompts_anon_read   ON public.prompts FOR SELECT USING (true);
CREATE POLICY prompts_auth_insert ON public.prompts FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY prompts_auth_update ON public.prompts FOR UPDATE TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY prompts_auth_delete ON public.prompts FOR DELETE TO authenticated USING (true);
```

Read posture matches `/api/collections` / `/api/sets`: anonymous
read, authenticated write. Every CREATE wrapped in `IF NOT EXISTS` /
`DO $$ ... $$` guard so the migration is idempotent.

## Backend

### Module layout

`backend/app/named_prompts/{__init__,models,service,router}.py`. Kept
parallel to `backend/app/prompts/` rather than nested under it: the
existing `prompts` module owns the scope-index endpoint and its
service, and conflating them would force a single module to express
two unrelated CRUD shapes.

### Models — `app/named_prompts/models.py`

```python
NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")

class Prompt(BaseModel):
    id: str
    scope_type: Literal["collection", "set"]
    scope_id: str
    name: str
    description: str
    body: str
    created_at: str
    updated_at: str
    created_by: str | None = None

class PromptCreate(BaseModel):
    scope_type: Literal["collection", "set"]
    scope_id: str
    name: str         = Field(pattern=NAME_RE.pattern, max_length=64)
    description: str  = Field(min_length=1, max_length=1024)
    body: str         = Field(min_length=1, max_length=256_000)

class PromptUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=1024)
    body: str | None        = Field(default=None, min_length=1, max_length=256_000)

class PromptListResponse(BaseModel):
    items: list[Prompt]
```

`scope_id` and `name` are immutable post-create. `PUT` only accepts
`description` and `body`. Renaming requires delete-and-recreate.

### Service — `app/named_prompts/service.py`

```python
def list_prompts_for_scope(db, scope_type, scope_id) -> list[Prompt]: ...
def list_effective_prompts_for_set(db, set_id) -> list[Prompt]:
    # Own + parent collection's prompts. Set-scoped wins on name conflict.
    ...
def get_prompt(db, prompt_id) -> Prompt | None: ...
def create_prompt(db, body: PromptCreate, created_by: str | None) -> Prompt:
    # Validate name regex, validate scope exists, insert with new UUID
    # and `now()` timestamps. Raise `IntegrityError` on UNIQUE violation
    # → translated to 409 in router.
    ...
def update_prompt(db, prompt_id, body: PromptUpdate) -> Prompt | None: ...
def delete_prompt(db, prompt_id) -> bool: ...
```

`list_effective_prompts_for_set`: SELECT named prompts where
`(scope_type='set' AND scope_id=:set_id)` UNION ALL
`(scope_type='collection' AND scope_id IN (parent collections of the
set))`. Result ordered: own first (alphabetical), then inherited
(alphabetical). Set-scoped name shadows Collection-scoped name with
the same string in the picker — implemented as a Python pass after
the SQL fetch (smaller blast radius than expressing the conflict
resolution in SQL).

### Router — `app/named_prompts/router.py`

| Method | Path | Auth | Body | Response |
|---|---|---|---|---|
| `GET` | `/api/named-prompts?scope_type=&scope_id=` | Anonymous | — | `200` `PromptListResponse` |
| `GET` | `/api/named-prompts/by-scope?collection_id=&set_id=` | Anonymous | — | `200` `PromptListResponse` (effective list) |
| `POST` | `/api/named-prompts` | Authenticated | `PromptCreate` | `201` `Prompt` / `409` on name collision / `400` on validation / `404` on scope not found |
| `GET` | `/api/named-prompts/{id}` | Anonymous | — | `200` `Prompt` / `404` |
| `PUT` | `/api/named-prompts/{id}` | Authenticated | `PromptUpdate` | `200` `Prompt` / `404` / `400` |
| `DELETE` | `/api/named-prompts/{id}` | Authenticated | — | `204` / `404` |

`by-scope` accepts either `collection_id` alone (returns that
collection's named prompts) or `set_id` alone (returns
`list_effective_prompts_for_set`). Both supplied → 400. Neither
supplied → 400.

### Registration — `backend/app/main.py`

```python
from app.named_prompts.router import router as named_prompts_router
...
app.include_router(named_prompts_router)
```

### `app/ai/scope_prompts.py` and `app/ai/service.py` — UNTOUCHED

Per ADR-154, named prompts do not auto-apply. The composition
pipeline reads `system_prompt` only.

## Scope-index extension

### Extend `app/prompts/models.py`

```python
EntryKind = Literal["system_prompt", "named_prompt"]

class ScopePromptIndexEntry(BaseModel):
    name: str                              # "set:<uuid>" | "set:<uuid>:<prompt-name>" | "collection:..."
    entry_kind: EntryKind                  # NEW (default "system_prompt" for backwards compat readers)
    scope_type: Literal["collection", "set"]
    scope_id: str
    scope_name: str
    description: str | None = None
    body: str
    prompt_name: str | None = None         # NEW — only set when entry_kind == "named_prompt"
```

### Extend `app/prompts/service.py:list_scope_prompts`

After the existing two SELECTs, append a third:

```sql
SELECT p.id, p.scope_type, p.scope_id, p.name, p.description, p.body,
       COALESCE(c.name, s.name) AS scope_name
FROM prompts p
LEFT JOIN collections c ON p.scope_type='collection' AND p.scope_id=c.id AND c.is_deleted=0
LEFT JOIN sets        s ON p.scope_type='set'        AND p.scope_id=s.id AND s.is_deleted=0
WHERE COALESCE(c.id, s.id) IS NOT NULL
ORDER BY p.scope_type, scope_name, p.name;
```

Map each row into a `ScopePromptIndexEntry` with
`name=f"{scope_type}:{scope_id}:{name}"`, `entry_kind="named_prompt"`,
`prompt_name=name`. Append after the existing system_prompt entries
in the response (so any client that processes them in order sees
system prompts first, named prompts second, both grouped predictably).

## iris-client

### Extend `IrisClient.list_scope_prompts() -> list[ScopePromptIndexEntry]`

The existing method continues to return all entries (system + named).
The model gains the two new fields (`entry_kind`, `prompt_name`).
Existing callers that ignored those fields keep working.

Forward compat: tolerate both `{"items": [...]}` and bare `[...]`,
unchanged from SPEC-152-A.

No new method needed. (The plan file mentioned `list_named_prompts()`
as a possibility; keeping the existing method and extending the model
is cleaner and avoids duplicate code paths in the MCP server.)

## MCP server

### Extend `mcp/src/iris_mcp/prompts.py`

Replace the existing `_NAME_RE` with a single regex that matches
both kinds:

```python
_NAME_RE = re.compile(
    r"^(?P<scope>set|collection):(?P<uuid>[0-9a-f-]{36})(?::(?P<prompt>[a-z][a-z0-9-]{0,63}))?$"
)
```

`list_prompts` — unchanged surface, now emits one entry per item from
`client.list_scope_prompts()` (which already returns both kinds after
the iris-client extension). For named-prompt entries, the description
shown in the picker uses the named prompt's own description, formatted
as `"{Scope}: {scope_name} — {prompt_name} — {prompt_description}"`,
truncated at 200 chars (existing rule). For system-prompt entries the
formatting is unchanged from SPEC-152-A.

`get_prompt` — match `_NAME_RE`. If `prompt` group is None, behave
exactly as today. If `prompt` group is set, look up the corresponding
named-prompt entry from `client.list_scope_prompts()` (matching on
`entry.name`) and build the preamble:

```
Loaded from Iris {Scope} "{scope_name}" — prompt "{prompt_name}" ({url}):

{body}
```

`{url}` falls back to the no-URL form if `IRIS_WEB_URL` is unset
(consistent with existing `_preamble`).

### `mcp/src/iris_mcp/server.py`

No changes — the existing `@server.list_prompts()` and
`@server.get_prompt()` decorators delegate to the (extended)
`iris_prompts` module functions.

## Web GUI

### `/sets/[id]` and `/collections/[id]` edit pages

Add a "Prompts" `<section>` below the existing "System prompt"
textarea (which stays for ADR-150 / discussion / create flows).

Layout per row:

```
[ name (immutable post-create) ]   [ description (single-line) ]
[ body (textarea, monospace, rows=8) ]
                                                 [ Save ] [ Delete ]
```

Plus a "+ Add prompt" button that appends an empty row (with name
field editable until first save).

Per-row CRUD via the existing `apiFetch<T>` wrapper (no batched form
submit — partial saves don't drop sibling edits). DOMPurify on every
input before send, per `{@html}` protocol §7.

Inheritance UI on `/sets/[id]`: below the editable Set-scoped
prompts, a read-only "Inherited from collection: <name>" group lists
parent-collection prompts (data from `/api/named-prompts/by-scope`
filtered to `entry.scope_type=='collection'`). Inheritance is
display-only; editing a parent prompt happens on the collection edit
page.

### Frontend types

Extend `frontend/src/lib/types/scope-prompts.ts` (or equivalent) with
`entry_kind` and `prompt_name`. Add `Prompt`, `PromptCreate`,
`PromptUpdate` types under `frontend/src/lib/types/named-prompts.ts`.

### Wrappers

`frontend/src/lib/api/named-prompts.ts` — typed wrappers around
`/api/named-prompts*`, mirroring the existing collections / sets
client wrappers.

## Tests

| File | Cases | Layer |
|---|---|---|
| `backend/tests/test_migrations/test_named_prompts_schema.py` | 6 (SQLite m048: table exists + correct columns + UNIQUE + INDEX; Supabase m052: same + RLS policies present; both: idempotency guard) | migration |
| `backend/tests/test_named_prompts/test_service.py` | 8 (create happy path; create with duplicate name → IntegrityError; list_prompts_for_scope ordering; list_effective_prompts_for_set inheritance + name shadowing; get_prompt 404; update changes only allowed fields; update non-existent → None; delete idempotent) | backend |
| `backend/tests/test_named_prompts/test_router.py` | 7 (POST happy path; POST validation error 400; POST duplicate 409; GET list filtered by scope; GET by-scope effective list; PUT update; DELETE 204; anonymous read posture verified) | backend |
| `backend/tests/test_prompts/test_router_named_prompts_extension.py` | 4 (scope-index includes named prompts; entry_kind discriminator on every entry; prompt_name set only on named entries; ordering: system prompts then named prompts) | backend |
| `iris-client/tests/test_scope_prompts_named.py` | 3 (model accepts new fields; entry_kind round-trip; prompt_name None for system entries) | iris-client |
| `mcp/tests/test_prompts_list_named.py` | 4 (named prompt appears in list; description format includes prompt_name; order matches scope-index; collection inheritance reflected via the scope-index level, not MCP-level filtering) | MCP |
| `mcp/tests/test_prompts_get_named.py` | 4 (named prompt happy path with three-segment name; preamble includes prompt_name; malformed three-segment name 400; unknown prompt_name on existing scope → ValueError) | MCP |
| `frontend/tests/sets-page-named-prompts.test.ts` | 4 (renders existing prompts; add row + save; edit row body; delete row) | frontend |
| `frontend/tests/collections-page-named-prompts.test.ts` | 4 (same four cases on collection page) | frontend |

Total: **44 new tests**.

Existing v5.8.x test suites must continue to pass. Key sentinel:
`backend/tests/test_ai/test_scope_prompts.py` (composition pipeline)
must show no behaviour change — named prompts are not in the
composition path.

## End-to-end verification

```bash
# Branch already created: feature/named-prompts-v5.9.0
./scripts/dev.sh start

# 1. Web GUI: navigate to /sets/<doview-book-set-id>
#    Section "System prompt" still shows existing content (unchanged).
#    Section "Prompts" shows empty list with "+ Add prompt" button.
#    Add named prompt:
#      name: "outcomes-theory-text-response"
#      description: "Apply Dr Paul Duignan's outcomes theory using only the Iris DoView Book set."
#      body: <Prompt A content drafted earlier in conversation>
#    Add named prompt:
#      name: "diagram-retrieval"
#      description: "Reproduce verbatim mermaid diagrams from the Iris DoView Book set."
#      body: <Prompt B content drafted earlier in conversation>

# 2. Backend round-trip:
curl -s "http://localhost:8000/api/named-prompts?scope_type=set&scope_id=33032180-d77a-4ce4-88cf-b49cd643e093" | jq '.items | length'   # → 2
curl -s "http://localhost:8000/api/prompts/scope-index" | jq '.items | map(select(.entry_kind=="named_prompt")) | length'  # → 2 (or more if other scopes also have named prompts)

# 3. MCP picker (in Claude Code with Iris MCP connected):
#    /iris:set:33032180-d77a-4ce4-88cf-b49cd643e093                                   → loads existing system_prompt
#    /iris:set:33032180-d77a-4ce4-88cf-b49cd643e093:outcomes-theory-text-response     → loads Prompt A
#    /iris:set:33032180-d77a-4ce4-88cf-b49cd643e093:diagram-retrieval                 → loads Prompt B

# 4. Run the test suite for each layer:
cd backend && pytest tests/test_named_prompts/ tests/test_migrations/test_named_prompts_schema.py tests/test_prompts/test_router_named_prompts_extension.py -v
cd ../mcp && pytest tests/test_prompts_list_named.py tests/test_prompts_get_named.py -v
cd ../iris-client && pytest tests/test_scope_prompts_named.py -v
cd ../frontend && npm test -- sets-page-named-prompts collections-page-named-prompts

# 5. Regression sentinels (must continue to pass):
cd ../backend && pytest tests/test_ai/test_scope_prompts.py tests/test_prompts/test_router.py -v
cd ../mcp && pytest tests/test_prompts_list.py tests/test_prompts_get.py -v
```

All 44 new tests pass; all existing v5.8.x tests still pass; manual
DoView Book invocation flow works in Claude Code's prompt picker
across all three names.

## Out of scope (deferred per ADR-154)

- Per-prompt `auto_apply` flag.
- Argument templating (`{{set.name}}` etc.).
- Per-user prompts.
- Skill bundles / multi-file resources.
- Local-file delivery (`.claude/skills/` sync).
- Reserved name collision protection (e.g. preventing a user creating
  a named prompt called `system_prompt` — current uniqueness is per
  `(scope_type, scope_id, name)`, and the MCP name format
  `set:<uuid>:<name>` doesn't collide with the system_prompt name
  `set:<uuid>`, so this isn't a v1 concern).
