# SPEC-150-A: Scope-level system prompts

ADR: [ADR-150](../ADR-150-Scope-Level-System-Prompts.md)

## Database schema

### Columns added

| Table | Column | SQLite type | Postgres type | Notes |
|---|---|---|---|---|
| `collections` | `system_prompt` | `TEXT` | `TEXT` | Nullable. Free-text. No length cap in DB; service layer warns above 16 000 chars. |
| `sets` | `system_prompt` | `TEXT` | `TEXT` | Same. |

### Migrations

- `backend/app/migrations/m047_scope_system_prompts.py` (SQLite —
  idempotent `ALTER TABLE` guarded by `PRAGMA table_info`).
- `backend/app/migrations/supabase/m051_scope_system_prompts.sql`
  (Postgres — `ALTER TABLE … ADD COLUMN IF NOT EXISTS`).

Numbering note: SQLite migrations are at m046; Supabase migrations
are at m050. The next SQLite slot is m047; the next Supabase slot is
m051. This skew is pre-existing (see m046_extensions_source.py vs
m048_extensions_source.sql).

## Composition logic

### `backend/app/ai/scope_prompts.py`

```python
async def build_scope_prompts(
    db: DatabasePort,
    *,
    set_ids: list[str],
    collection_id: str | None,
) -> str:
    """Return the scope prepend text, or "" when no prompts apply.

    Composition order:
      [collection prompt 1]
      [collection prompt 2]   # multi-collection multi-set ask
      [set prompt 1]
      [set prompt 2]

    Each non-empty prompt is followed by a blank line.

    Collection prompts are deduplicated by collection id. If
    `collection_id` is supplied explicitly, it's used; otherwise the
    parent collection is derived per set from `sets.collection_id`.
    """
```

Behavioural rules:

1. If `set_ids` is empty (multi-set with only docref / file context),
   and `collection_id` is None, return `""`.
2. Otherwise, look up the set rows in `set_ids` order and gather
   `system_prompt` and `collection_id` per set.
3. Build a unique-by-id, order-preserving list of collection ids.
   When `collection_id` arg is non-None, place it first.
4. Fetch each collection's `system_prompt`. Skip empties.
5. Append each set's `system_prompt`. Skip empties.
6. Join with `\n\n`. If empty, return `""`.

### Wiring points

All four sites concatenate the prepend ahead of the existing
`system_content`:

- `backend/app/ai/router.py::_ask_streaming` (single-set discuss /
  creation). Derive collection from the set row.
- `backend/app/ai/router.py::_ask_multi_set_streaming` (multi-set;
  `body.collection_id` may be supplied).
- `backend/app/ai/service.py::ask_question` (non-streaming single).
- `backend/app/ai/service.py::ask_multi_set_question` (non-streaming
  multi).

Pseudocode for the wiring (identical at each site):

```python
scope_prepend = await build_scope_prompts(
    db, set_ids=[set_id], collection_id=None,
)
# … existing composition that produces `system_content` …
if scope_prepend:
    system_content = f"{scope_prepend}\n\n{system_content}"
if len(system_content) > 16_000:
    log.warning(
        "[AI_DEBUG] composed system_content is %d chars (>16000)",
        len(system_content),
    )
```

## API

### `PUT /api/collections/{id}`

`CollectionUpdate` adds a `system_prompt: str | None = None` field.
The `update_collection` service writes it to the `system_prompt`
column. `CollectionResponse` includes it on read.

### `PUT /api/sets/{id}`

Same shape on `SetUpdate` and `SetResponse`. `update_set` persists
the value. The `collection_id` parameter and validation are
unchanged.

### No new endpoints

Phase 1 reuses the existing CRUD endpoints; the system prompt rides
in the same PUT body the frontend already sends.

## Frontend

### `frontend/src/routes/collections/[id]/+page.svelte`

Add a System prompt section below the Description field:

```svelte
<label class="block">
  <span class="text-sm font-medium">System prompt</span>
  <textarea
    bind:value={systemPrompt}
    rows="6"
    maxlength="20000"
    placeholder="Optional. Prepended to every AI question about Sets in this Collection."
    class="…"
  ></textarea>
  <span class="text-xs text-muted">
    Inherited by every Set in this Collection.
  </span>
</label>
```

`handleSave` includes `system_prompt: DOMPurify.sanitize(systemPrompt)`
in the PUT body alongside `name` / `description`.

### `frontend/src/routes/sets/[id]/+page.svelte`

Same control. Helper text: "Optional. Applied in addition to the
parent Collection's system prompt."

### Sanitisation

`DOMPurify.sanitize` is applied for parity with how description is
handled today, even though the textarea content goes to the model
as plain text. Defence in depth: prevents `<script>`-shaped junk
from being persisted if a user pastes HTML.

## Tests

| File | Coverage |
|---|---|
| `backend/tests/test_migrations/test_scope_system_prompts_schema.py` | Static-parser test: SQLite m047 adds `system_prompt` to both `collections` and `sets`; Supabase m051 uses `ADD COLUMN IF NOT EXISTS system_prompt`. |
| `backend/tests/test_ai/test_scope_prompts.py` | `build_scope_prompts` unit tests: empty scope returns ""; single-set with collection prompt; single-set without collection; multi-set same collection (dedup); multi-set multi-collection (preserves order); explicit `collection_id` arg overrides derived order. |
| `backend/tests/test_collections/test_router.py` | New cases: PUT with `system_prompt` persists; GET returns it; legacy PUT without the field is non-destructive (preserves the existing value). |
| `backend/tests/test_sets/test_router.py` | Same as collections. |
| `backend/tests/test_ai/test_ask_with_scope_prompts.py` | Integration: with a mocked provider, asking about a set whose collection has a prompt yields a `system_content` that contains the collection prompt then the set prompt then the existing provider/context body. |

## Observability

`[AI_DEBUG]` log lines on each ask path already record system content
length. Add a `WARNING` when length > 16 000 chars (separate line so
it stays visible in production logs even if `AI_DEBUG` is off).

## Migration safety

The migrations are additive `ALTER TABLE ADD COLUMN` only. No data
backfill, no constraint changes, no index changes. Rollback path is
not provided (consistent with every other migration in the project)
but is trivially `DROP COLUMN` should it ever be needed.

## Out of scope (deferred per ADR-150)

- Per-user / per-conversation prompt overrides.
- Prompt templating / variable substitution.
- Per-mode (discuss vs creation) split prompts.
- Versioning / change history of the prompt text. (Service-layer
  audit log captures who changed it via the existing `updated_at`
  bump.)
