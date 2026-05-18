# SPEC-204-A: Per-set tab defaults

Implements: [ADR-204](../ADR-204-Per-Set-Tab-Defaults.md)
Status: Living

## Data model

Two columns added to `sets`:

```
package_tab_default TEXT NOT NULL DEFAULT 'relationships'
view_tab_default    TEXT NOT NULL DEFAULT 'canvas'
```

Enum values enforced at the Pydantic layer:

```python
PackageTabDefault = Literal['relationships', 'details']
ViewTabDefault    = Literal['canvas', 'relationships', 'details']
```

DB stores TEXT. No SQL CHECK constraint (Protocol §15 — keeps SQLite
and Supabase ALTER syntax identical).

## Sort behaviour

Not a sort — a default-active-tab. The frontend reads the value on
initial page load and seeds its `activeTab` state. Subsequent clicks
update local state only; they do not write back to the set.

## Request / response

`PUT /api/sets/{id}` accepts two optional fields:

```ts
{
  // existing fields...
  package_tab_default?: 'relationships' | 'details' | null  // null = leave alone
  view_tab_default?: 'canvas' | 'relationships' | 'details' | null
}
```

`GET /api/sets/{id}` and `GET /api/sets` always return both fields,
defaulting to `'relationships'` / `'canvas'` for any row that lacks
them (defensive against the brief pre-migration window on Supabase).

## Frontend

`/sets/{id}` edit page adds two `<select>`s under the hierarchy_sort
control:

```svelte
<label for="set-edit-package-tab-default">Package tab default</label>
<select id="set-edit-package-tab-default" bind:value={packageTabDefault}>
  <option value="relationships">Relationships</option>
  <option value="details">Details</option>
</select>

<label for="set-edit-view-tab-default">View tab default</label>
<select id="set-edit-view-tab-default" bind:value={viewTabDefault}>
  <option value="canvas">Canvas</option>
  <option value="relationships">Relationships</option>
  <option value="details">Details</option>
</select>
```

State seeded from `setData.package_tab_default` /
`setData.view_tab_default` on load. Included in the PUT body on
save. Round-trips through `IrisSet.package_tab_default` and
`IrisSet.view_tab_default`.

### `/packages/{id}`

`activeTab` initialiser reads `set.package_tab_default` once the
parent set is loaded. DOM order:

```
Relationships → Details → Version History
```

### `/views/{id}`

`activeTab` initialiser reads `set.view_tab_default`. DOM order:

```
Canvas → Relationships → Details → Version History
```

`userSelectedTab` (existing flag in `/views/{id}`) suppresses the
re-seed if the user has already manually clicked a tab after load.

## MCP

`update_set` tool's schema documents both fields. The
`_put_merge_partial` helper preserves whatever value is currently
stored when the caller omits the field. Callers can update just
one:

```
update_set(set_id="...", package_tab_default="details")
update_set(set_id="...", view_tab_default="relationships")
```

## CLI

`iris update set --json '{"package_tab_default":"details"}'` works
unchanged via the body passthrough. Surface parity is preserved.

## Acceptance criteria

1. New sets default to `package_tab_default='relationships'` and
   `view_tab_default='canvas'`.
2. Existing sets (pre-migration) report the same defaults via the
   API (Pydantic default + service-layer fallback).
3. Setting `package_tab_default='details'` causes `/packages/{x}` for
   packages in that set to open on Details.
4. Setting `view_tab_default='details'` causes `/views/{x}` for
   diagrams in that set to open on Details.
5. Invalid value in PUT body returns 422 (Pydantic `Literal`).
6. MCP `update_set` accepts both fields; GET-then-merge preserves
   them across unrelated updates.
7. DOM order in Packages screen: Relationships before Details.
8. DOM order in Views screen: Details after Relationships, before
   Version History.
9. `scripts/check_surface_parity.py` stays clean.

## Tests

Migration schema — `backend/tests/test_migrations/test_sets_default_tabs_schema.py`:

1. SQLite `m069` adds both columns with right type + defaults.
2. SQLite `m069` is idempotent (PRAGMA check).
3. Supabase `m073` adds both columns with right type + defaults.
4. Supabase `m073` uses `IF NOT EXISTS` per column.
5. Supabase `m073` references the SQLite mirror in its header.
6. Supabase `m073` has no bare boolean integer literals
   (Protocol §15 regression guard).
7. Defaults match across modes.
8. Both columns are TEXT NOT NULL.

Backend behaviour — `backend/tests/test_sets/test_default_tabs.py`:

1. `POST /api/sets` returns `package_tab_default='relationships'`,
   `view_tab_default='canvas'`.
2. `GET /api/sets/{id}` returns the current values.
3. `PUT /api/sets/{id}` with `package_tab_default='details'`
   persists.
4. `PUT` with only `view_tab_default` leaves `package_tab_default`
   alone.
5. Invalid value returns 422.

## Release ordering (Supabase)

Per the "Render+Supabase release ordering" memory:

1. Merge PR.
2. Run `scripts/supabase-migrate.sh` against Supabase DB.
3. Render auto-deploys on push.

Service-layer fallback in `_row_to_dict` keeps the API non-fatal if
the migration trails briefly — sets just return the new defaults.

## Verification

```
.venv/bin/python -m pytest \
  backend/tests/test_migrations/test_sets_default_tabs_schema.py \
  backend/tests/test_sets/test_default_tabs.py
.venv/bin/python scripts/check_surface_parity.py
```
