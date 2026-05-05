# ADR-135: DocRef Supabase migration parity

Status: Accepted (2026-05-04) — amended 2026-05-05 (issue #27)

## Context

The DocRef extension ([ADR-112](ADR-112-DocRef-Legislation-Extension.md))
ships two tables — `docref_documents` and `docref_chunks` — created by
the SQLite Python migration `backend/app/migrations/m034_docref_tables.py`.

When Iris is deployed in Supabase mode (`IRIS_DB_BACKEND=supabase`), the
backend deliberately skips Python migrations
(`backend/app/startup.py::_initialize_supabase`) and instead applies the
SQL files in `backend/app/migrations/supabase/`. Those files were never
extended with the DocRef schema. The Supabase `m034` slot is occupied by
`m034_extensions.sql` (the Extensions registry from ADR-103), so the
numbering looked complete on inspection — there was no obvious gap to
flag the omission.

The result on render-supabase-uat (issue #24): the DocRef router runs
its first SELECT against a non-existent `docref_documents` table,
asyncpg raises, the FastAPI handler returns 500, and the frontend
`DocRefSelector.svelte` catches it and renders **"Failed to load
documents"**. The Iris AI Legislation feature is unusable on every
Supabase deployment.

## Decision

**Ship `m043_docref_tables.sql`** as the Postgres equivalent of the
SQLite m034 schema, and **adopt as a project rule that every Python
migration creating tables for an opt-in extension must ship a Supabase
SQL counterpart in the same change.**

The rule applies even when the extension is disabled by default. The
table needs to exist before the extension can be installed; if the
schema isn't there, install fails the moment the user opts in. The
Supabase migration must be present alongside the SQLite migration on
the same branch — they're a single decision expressed twice.

## Why not "fix the numbering" instead

The two migration trees have already diverged numerically (SQLite m034
= DocRef tables, Supabase m034 = Extensions registry). Renumbering one
to match the other would invalidate every existing deployment's idea
of which migrations have been applied. The rule we're adopting cares
about the *content* being mirrored, not the *number* — Supabase numbers
are a separate sequence.

The new file lands at the next free Supabase slot (`m043`), not at any
particular SQLite-aligned number. This is fine: the Supabase runner
applies in lex order, and idempotent `CREATE TABLE IF NOT EXISTS` makes
re-runs safe.

## Why not block the route at the adapter

We could detect "table missing" at adapter level and return a friendlier
error than 500. That treats a symptom; the actual fix has to put the
tables in place. Once the tables exist on Supabase, every other
extension that follows the same pattern (DocRef-style opt-in tables on
both backends) gets the right behaviour for free.

## Why not auto-run Python migrations on Supabase

The original choice to skip Python migrations on Supabase
(`_initialize_supabase`) was deliberate: the Python migrations contain
SQLite-only operations (`PRAGMA`, `executescript`, table-recreation
ALTERs) that don't translate cleanly to Postgres. Reversing that
decision would re-introduce the maintenance hazard the split was
designed to avoid. Mirroring schemas in two source files is the
trade-off we're keeping.

## Verification

`backend/tests/test_migrations/test_docref_schema.py` (added in the
same change) parses `m043_docref_tables.sql` and asserts:

- The file exists.
- Both tables are created.
- All columns the service layer reads in `_SELECT` and writes in
  INSERT/UPDATE statements are present.
- `docref_chunks.document_id` REFERENCES `docref_documents(id)
  ON DELETE CASCADE`.
- Both unique constraints (`UNIQUE(slug, latest_version)`,
  `UNIQUE(document_id, chunk_id)`) are present.
- The three SQLite indexes are mirrored.
- RLS is enabled on both tables (the m030 invariant for new tables).

The tests are static parsers — they run in standard CI without a
Postgres container. A live Postgres validation belongs in deployment
smoke tests rather than the unit suite.

## Compatibility

- SQLite deployments are unaffected — the Python migration `m034` still
  runs as before.
- Supabase deployments that have already received the empty-tables
  failure can apply `m043_docref_tables.sql` against an existing
  database; the migration is `CREATE TABLE IF NOT EXISTS` and idempotent,
  so re-running the full Supabase migration set is safe. The
  deployment guide is updated to call this out (m041–m043).

## See also

- [ADR-103](ADR-103-Extensions-Framework.md) — extensions framework.
- [ADR-112](ADR-112-DocRef-Legislation-Extension.md) — DocRef as the
  first opt-in extension; this ADR fills its Supabase gap.
- [SPEC-135-A](specs/SPEC-135-A-DocRef-Supabase-Migration.md) — schema
  reference and verification steps.

## Amendment 2026-05-05 — fire-and-forget import (issue #27)

UAT against render-supabase-uat surfaced a second bug stacked on top of
the original schema problem: even after the tables existed, importing a
real document (e.g. the Social Security Act) reliably surfaced
**"Import failed"** in the frontend, while the backend continued and
the import actually completed a few seconds later. The user could
refresh the screen and see the document marked imported.

The root cause is the synchronous import pipeline in
`app/docref/service.py::import_document` — it downloads a CSV
(potentially many MB), then issues one INSERT per chunk inside the
request thread. On Render's Postgres path each round-trip is on the
order of 10–30 ms; a few thousand chunks crosses Render's edge
request-timeout (~100s). The edge closes the connection, the frontend
catches a network/HTTP error and sets `error = 'Import failed'` — but
the asyncio task on the backend keeps going, commits the rows, and
flips status to `imported`.

**Decision:** make the import endpoint fire-and-forget.

- A new `start_import_document` service method sets the row's status to
  `importing` synchronously and returns immediately.
- The router (`app/docref/router.py`) launches the actual download and
  insert via `asyncio.create_task` and returns **HTTP 202** with the
  `importing` status.
- The frontend (`DocRefSelector.svelte`) polls `/api/docref/documents`
  every ~3 s while any document is in `importing` state and stops
  polling once everything settles. It also applies an optimistic local
  status flip so the spinner shows the moment the user clicks.

This matches the existing background-task pattern used for MNEMOS
reindex and DocRef index refresh (`asyncio.create_task` from
`extensions/router.py`) — no new infrastructure, no Celery/Redis.

The synchronous `import_document` function is preserved for tests and
direct backend invocation; only the HTTP route now delegates to it via
a background task.
