# SPEC-202-A: Per-set hierarchy sort

Implements: [ADR-202](../ADR-202-Per-Set-Hierarchy-Sort-Preference.md)
Status: Living

## Data model

Column added to `sets`:

```
hierarchy_sort TEXT NOT NULL DEFAULT 'manual'
```

Enum values enforced at the Pydantic layer (`HierarchySort =
Literal['manual','alpha','newest','oldest']`). DB stores TEXT.

## Sort behaviour

The ORDER BY clause appended to the UNION in `get_diagram_hierarchy`:

| Value | ORDER BY | Note |
|---|---|---|
| `manual` | `t.node_type, t.sequence_order, t.name` | Diagrams first (alphabetical 'diagram' < 'package'), then creation-order, then name. |
| `alpha` | `LOWER(t.name)` | Packages and diagrams interleave alphabetically (case-insensitive). |
| `newest` | `t.created_at DESC` | Latest first. |
| `oldest` | `t.created_at ASC` | Earliest first. |

The whitelist (`_HIERARCHY_ORDER_BY` dict in
`backend/app/diagrams/service.py`) means the value is never
string-formatted from user input — it's looked up by key. Invalid
values fall back to `'manual'` defensively.

`created_at` is added to both arms of the UNION SELECT so the
date-based modes have the column they need.

## Request / response

`PUT /api/sets/{id}` accepts an optional `hierarchy_sort` field:

```ts
{
  name: string,
  description: string | null,
  thumbnail_source: ...,
  thumbnail_diagram_id: ...,
  collection_id: ...,
  system_prompt: ...,
  mcp_system_context: ...,
  hierarchy_sort?: 'manual' | 'alpha' | 'newest' | 'oldest' | null  // null = leave alone
}
```

`GET /api/sets/{id}` and `GET /api/sets` always include
`hierarchy_sort` in the response, defaulting to `'manual'` for any
row that somehow lacks the value (belt-and-braces against
pre-migration data).

## Frontend

`/sets/{id}` edit page adds a `<select>` between Collection and
System prompt:

```svelte
<label for="set-edit-hierarchy-sort">Hierarchy sort</label>
<select id="set-edit-hierarchy-sort" bind:value={hierarchySort}>
  <option value="manual">Manual (drag-and-drop)</option>
  <option value="alpha">Alphabetical (A → Z)</option>
  <option value="newest">Newest first</option>
  <option value="oldest">Oldest first</option>
</select>
```

State seeded from `setData.hierarchy_sort` on load; included in
the PUT body on save. Round-trips through `IrisSet.hierarchy_sort`
(typed `HierarchySort`).

## MCP

`update_set` tool's schema documents `hierarchy_sort`. The
`_put_merge_partial` helper preserves whatever value is currently
stored when the caller omits the field. Callers can update
just the sort:

```
update_set(set_id="...", hierarchy_sort="alpha")
```

## Acceptance criteria

1. New sets are created with `hierarchy_sort = 'manual'`.
2. Existing sets (pre-migration) report `hierarchy_sort = 'manual'`
   via the API.
3. Setting `hierarchy_sort = 'alpha'` causes
   `/api/diagrams/hierarchy?set_id=...` to return items ordered
   case-insensitively by name, interleaved across packages and
   diagrams.
4. `'newest'` returns items in `created_at DESC` order.
5. `'oldest'` returns items in `created_at ASC` order.
6. An invalid value in the PUT body returns 422 (Pydantic
   `Literal` validation).
7. The MCP `update_set` tool accepts `hierarchy_sort` and the GET-
   then-merge path preserves it across other updates.
8. `scripts/check_surface_parity.py` stays clean.

## Tests

Backend behaviour — `backend/tests/test_diagrams/test_hierarchy_sort.py`:

1. New set defaults to `'manual'`.
2. Existing sets keep manual order (diagrams first, then packages
   in creation order — locks in the current behaviour as a
   regression guard).
3. `'alpha'` interleaves packages and diagrams alphabetically.
4. `'newest'` returns newest-first.
5. `'oldest'` returns oldest-first.
6. Invalid value returns 422.
7. `GET /api/sets/{id}` returns the current `hierarchy_sort`.

Migration schema — `backend/tests/test_migrations/test_sets_hierarchy_sort_schema.py`:

1. SQLite `m068` adds the column with the right type + default.
2. SQLite `m068` is idempotent via PRAGMA check.
3. Supabase `m072` adds the column with the right type + default.
4. Supabase `m072` uses `IF NOT EXISTS`.
5. Supabase `m072` references the SQLite mirror in its header.
6. Supabase `m072` has no bare boolean integer literals (Protocol §15 regression guard).
7-8. Defaults and column types match across modes.

## Release ordering (Supabase)

Per the standing "Render+Supabase release ordering" memory:

1. Merge this PR (migration + code).
2. Run `scripts/supabase-migrate.sh` against the Supabase DB.
3. Render auto-deploys on push — the new code path finds the
   column ready.

The service layer's `try/except` around the `SELECT hierarchy_sort`
makes the deploy window non-fatal if the migration lags briefly —
the hierarchy falls back to `'manual'` ordering until the column
exists. Once the migration runs, ordering picks up the per-set
preference.

## Verification

```
.venv/bin/python -m pytest \
  backend/tests/test_diagrams/test_hierarchy_sort.py \
  backend/tests/test_sets/ \
  backend/tests/test_migrations/test_sets_hierarchy_sort_schema.py
.venv/bin/python scripts/check_surface_parity.py
```

All green. Manual smoke per ADR-202.
