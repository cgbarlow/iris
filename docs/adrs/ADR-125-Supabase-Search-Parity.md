# ADR-125: Supabase Search Parity With SQLite

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-125 |
| **Initiative** | Search |
| **Proposed By** | Engineering |
| **Date** | 2026-04-21 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** Iris shipping v4.1.1 with a frontend dashboard-
search-scope fix (ADR-121) and per-operation FTS5 index calls for
packages/sets/collections on SQLite — both changes that closed the "search
doesn't work" symptom on local SQLite deployments — yet leaving two
backend-side gaps on the Supabase/PostgreSQL deployment that powers UAT,

**facing** a user-reported repeat of the search regression on UAT: typing
"msd" on the dashboard with no filters should return package
`6b1e3411-0e87-48c0-a7da-3965c6d55905` ("NZ Ministry of Social Development
(MSD) ...") plus two diagram IDs `d9172782-...` and `2da6d36d-...`, but
returns nothing. Inspection of `backend/app/search/service.py::_search_postgres`
and `backend/app/migrations/supabase/m002_*.sql` reveals **two independent
bugs** behind the symptom: (a) `_search_postgres` only queries `elements`
and `diagrams` — packages/sets/collections have no `search_vector` columns
at all in Postgres, so admin-created packages are not searchable at the
database level; and (b) the existing `BEFORE INSERT OR UPDATE ON elements`
and `BEFORE INSERT OR UPDATE ON diagrams` triggers read from
`element_versions` / `diagram_versions` at trigger time, but services
insert the version row *after* the parent row, so the parent row's
`search_vector` is **empty on initial create** — only subsequent updates
populate it. UAT packages and recently-imported diagrams are therefore
invisible to search,

**we decided for** **a single Supabase-only migration that restores full
search parity with SQLite**:

1. Add `search_vector TSVECTOR` columns + GIN indexes to `packages`,
   `sets`, and `collections`, mirroring the existing `elements`/`diagrams`
   pattern from `m002`.
2. Add `BEFORE INSERT OR UPDATE` trigger functions on each of the five
   entity tables (two existing + three new) that compute the vector from
   the best source available (version table for packages, direct columns
   for sets/collections).
3. **Fix the INSERT ordering bug** by adding `AFTER INSERT OR UPDATE ON
   element_versions / diagram_versions / package_versions` triggers that
   re-run an `UPDATE parent SET current_version = current_version WHERE
   id = NEW.<parent>_id` — a no-op write that re-fires the parent's BEFORE
   trigger with the version row now present, populating the vector. This
   preserves the existing single source of truth for vector construction
   (the BEFORE trigger functions).
4. Backfill every existing row via a `NOTIFY`-style UPDATE to re-fire
   triggers: `UPDATE packages SET current_version = current_version`
   (same pattern for each entity type) so UAT data becomes searchable
   immediately on deploy without a separate script.
5. Extend `_search_postgres` to UNION-style query packages + sets +
   collections in addition to elements + diagrams, matching the shape of
   `_search_sqlite` exactly. Scope filters (set / collection) apply
   uniformly,

**and neglected** (a) converting the BEFORE trigger into an AFTER trigger
directly — AFTER triggers cannot modify NEW, so the schema would need a
separate UPDATE statement; the chain-trigger pattern above keeps the
vector-computation code in one place; (b) a service-layer re-save call
after every create (mirroring SPEC-125 could have been a backend
workaround) — would move the indexing logic from the database layer to
the service layer, splitting responsibility; (c) backfilling via a
separate Python script after deploy — adds an operational step to every
release and can be forgotten; the in-migration UPDATE is atomic and
reliable; (d) returning to SQLite for UAT to avoid the Supabase-specific
work — defeats the dual-backend architecture and does not help any future
production deployment,

**to achieve** feature-complete full-text search on every Iris deployment
— SQLite and Supabase produce identical search results for the same query
against the same data, covering all five entity types, for both freshly-
created and pre-existing rows, with no operational follow-up after
migration,

**accepting that** the chain-trigger pattern fires an extra no-op UPDATE
on the parent table for every version insert — adds one row-lock per
create; measurable impact is negligible at Iris's scale (≤ thousands of
creates per deploy) and only occurs once per entity lifecycle; accepting
that the migration's backfill touches every existing row in
packages/sets/collections/elements/diagrams (≤ ~1300 rows on current UAT
— fast); accepting that `_search_postgres` now issues five queries
instead of two — the relational round-trip overhead on a pooler-fronted
connection is small compared to the ts_rank computation inside each
query; accepting that this work does not address the **frontend** side of
the dashboard search issue (that was already fixed in v4.1.0 — ADR-121 —
and is verified independent of this migration).

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| Supabase Search Parity | Migration `m040_search_all_entities.sql` adds `search_vector` columns + GIN indexes to `packages`, `sets`, `collections`. Trigger functions for all five entity tables (elements, diagrams, packages, sets, collections). Chain-trigger `AFTER INSERT OR UPDATE ON *_versions` that re-fires the parent table's BEFORE trigger, fixing the INSERT-ordering gap that left freshly-created elements/diagrams/packages unsearchable. Full backfill at migration time. `_search_postgres` extended to query all five tables, matching `_search_sqlite` feature-for-feature. | _inline — single-commit change, no separate SPEC needed_ |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Extends | ADR-121 | Dashboard Search Scope | Frontend fix already shipped in v4.1.0 — this ADR closes the backend-side gap on Supabase specifically. |

---

## References

Inline decision; implementation lives in `backend/app/migrations/supabase/m040_search_all_entities.sql` and `backend/app/search/service.py::_search_postgres`.

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-04-21 |
| Approved | Engineering | 2026-04-21 |
