# ADR-202: Per-set hierarchy sort preference

Status: Accepted (2026-05-18)

## Context

User feedback (post v6.10.x UAT): the diagram/package hierarchy that
shows under each set was sorted by an opaque rule. Reading
`backend/app/diagrams/service.py:get_diagram_hierarchy`, the order
was:

```sql
ORDER BY t.node_type, t.sequence_order, t.name
```

So diagrams always rendered above packages within a parent, then
items sorted by `sequence_order` (auto-incremented per parent on
create — effectively creation order within a node-type group), then
name as a final tiebreak.

That's the right default for users who rely on the drag-and-drop
reorder UI, but wrong for people who want **alphabetical** browsing
(particularly catalogue-style sets with dozens of packages) or
**newest-first** for fast-moving sets. There was no way to opt
into a different ordering.

## Decision

Add a `hierarchy_sort` TEXT column to the `sets` table. Each set
owns its own preference; the column value selects the ORDER BY
clause applied in `get_diagram_hierarchy`.

### Enum values

| Value | ORDER BY | Use case |
|---|---|---|
| `manual` | `t.node_type, t.sequence_order, t.name` | Current behaviour. Diagrams above packages, then drag-and-drop order. **Default.** |
| `alpha` | `LOWER(t.name)` | Alphabetical, case-insensitive. Packages and diagrams interleave. |
| `newest` | `t.created_at DESC` | Latest items at the top. Catalogue / changelog browsing. |
| `oldest` | `t.created_at ASC` | Oldest items at the top. Archive browsing. |

### Enum enforcement

At the Pydantic layer (`HierarchySort = Literal[...]`), not via a
SQL `CHECK` constraint. Rationale: keeps the SQLite ↔ Supabase
migration syntax **identical** — Protocol §15. CHECK constraints
have slightly different syntax across the two engines (SQLite's
`ALTER TABLE ADD COLUMN` accepts column-level CHECK, but the
Postgres mirror would need a named constraint). Application-layer
validation is the single source of truth and keeps the schema
minimal.

### Migration (paired §15)

- SQLite: `m068_sets_hierarchy_sort.py` — PRAGMA-based idempotency,
  `ALTER TABLE sets ADD COLUMN hierarchy_sort TEXT NOT NULL DEFAULT 'manual'`.
- Supabase: `m072_sets_hierarchy_sort.sql` — `ADD COLUMN IF NOT EXISTS …`.

Default `'manual'` on the column means existing sets and pre-
migration rows automatically inherit current behaviour. No back-
fill required.

### API surface

- `SetUpdate.hierarchy_sort: HierarchySort | None = None` — None
  means "leave alone", preserving compatibility with `_put_merge_partial`
  (MCP) and any future partial-update client.
- `SetResponse.hierarchy_sort: HierarchySort = "manual"` — always
  returned; clients can read the current value.
- No new endpoint; the existing `PUT /api/sets/{id}` carries it.

### MCP

`_SET_UPDATE_FIELDS` adds `hierarchy_sort`. The `update_set` tool's
input schema documents the four values. Existing MCP clients
calling `update_set` without the field continue to work — the GET-
then-merge helper preserves whatever's currently stored.

### Frontend

Set edit page (`frontend/src/routes/sets/[id]/+page.svelte`) gets a
4-option `<select>` between Collection and System prompt sections,
wired to `hierarchySort` state which round-trips through `IrisSet`.

## Why per-set rather than global or per-user

Per-set:
- Different sets have different purposes — a curated reference set
  benefits from alphabetical; a working draft benefits from manual
  ordering.
- The user can decide once per set; no friction at view time.

Global was rejected: too coarse — locks every set to one rule.
Per-user was rejected: would require a separate user-preferences
table and reconciliation when multiple users browse the same set.
Per-set is the right grain.

## Why apply everywhere the hierarchy surfaces

The endpoint is `GET /api/diagrams/hierarchy?set_id=X`. Every
consumer (dashboard, packages page sidebar, views page tree) calls
that endpoint with the set_id. Centralising the sort in the
endpoint means consistency is free — every surface shows the same
order, set by the set owner once.

## Why no per-tab / per-component override

Out of scope. The user asked for a per-set setting; per-component
overrides add a control to every component that renders the tree
and proliferate state. Can be a follow-up if a real use case
emerges.

## Release ordering (Supabase)

This PR ships **migration + code together** per the autonomous goal.
The standing memory ("Render+Supabase release ordering") applies:
the Supabase migration (`m072`) must be applied before the code
deploys, otherwise `SELECT hierarchy_sort FROM sets WHERE id = ?`
would error. The service layer has a defensive `try/except` that
falls back to `'manual'` if the column lookup fails, so a brief
window without the migration is degraded but not broken.

The release-notes call out the recommended sequence:
1. Merge PR (migration + code).
2. Run `scripts/supabase-migrate.sh` against the Supabase DB.
3. Render auto-deploys on the merge; the new code path will find
   the column ready.

## Consequences

- `backend/app/migrations/m068_sets_hierarchy_sort.py` — new SQLite migration.
- `backend/app/migrations/supabase/m072_sets_hierarchy_sort.sql` — Supabase mirror.
- `backend/tests/test_migrations/test_sets_hierarchy_sort_schema.py` — 8 schema tests.
- `backend/app/startup.py` — m068 registered in the run-all-migrations sequence.
- `backend/app/sets/models.py` — `HierarchySort` Literal, fields on
  `SetUpdate` (optional) and `SetResponse` (required, default 'manual').
- `backend/app/sets/service.py` — `_SET_COLUMNS`, `_row_to_dict`,
  `create_set` and `update_set` carry `hierarchy_sort`. Update SQL
  is a separate UPDATE statement triggered only when non-None.
- `backend/app/sets/router.py` — pass `body.hierarchy_sort` through.
- `backend/app/diagrams/service.py` — `_HIERARCHY_ORDER_BY` whitelist
  + sort-key resolution at the top of `get_diagram_hierarchy`; new
  `created_at` selected in the UNION query; defensive fallback to
  `'manual'` if the column lookup fails.
- `backend/tests/test_diagrams/test_hierarchy_sort.py` — 7 behavioural
  tests across the 4 sort modes, default, response shape, invalid
  value rejection.
- `mcp/src/iris_mcp/tools.py` — `_SET_UPDATE_FIELDS` extended;
  `update_set` schema gets the field with documentation.
- `frontend/src/lib/types/api.ts` — `HierarchySort` exported,
  `IrisSet.hierarchy_sort` field.
- `frontend/src/routes/sets/[id]/+page.svelte` — state, load, save,
  and a `<select>` between Collection and System prompt.
- CHANGELOG `[6.11.0]`. Minor bump.

## Verification

```
.venv/bin/python -m pytest backend/tests/test_diagrams/test_hierarchy_sort.py \
                            backend/tests/test_sets/ \
                            backend/tests/test_migrations/test_sets_hierarchy_sort_schema.py
.venv/bin/python scripts/check_surface_parity.py
```

71 passed; parity clean.

Manual smoke: open `/sets/{id}`, change Hierarchy sort to
"Alphabetical (A → Z)", Save, then visit a page that renders this
set's hierarchy (dashboard / packages page sidebar) and confirm
items are now interleaved alphabetically.

## See also

- Issue [#173](https://github.com/cgbarlow/iris/issues/173) — the
  original UAT batch where the hierarchy sort question came up.
- Hierarchy endpoint: `backend/app/diagrams/service.py:get_diagram_hierarchy`.
- §15 Migration parity: `docs/protocols.md`.
