# ADR-094: Optional Supabase/Netlify Cloud Deployment

**Status:** Accepted
**Date:** 2026-03-21
**Depends on:** ADR-003 (Repository Architecture), ADR-004 (Auth/RBAC)

## Context

Iris currently runs as a self-contained application: FastAPI + SQLite on a single host, with the
frontend served from the same machine or a reverse proxy. This is ideal for on-premises, air-gapped,
or local-development deployments but requires infrastructure management (server, storage, backups).

There is demand for a **zero-infrastructure cloud deployment path** where Iris can be hosted on
Netlify (frontend + serverless API) backed by Supabase (PostgreSQL + auth). This must be optional —
the existing SQLite deployment must remain the default and must not be broken.

The key technical challenge is that the existing backend uses raw async SQLite queries via aiosqlite
across 30+ service modules (364 `await db.execute()` calls). PostgreSQL uses a different driver
(asyncpg) with different parameter placeholder syntax (`$1` vs `?`) and different built-in functions.

## Decision

Introduce an **optional Supabase/Netlify deployment mode** controlled by `IRIS_DB_BACKEND=supabase`.

**Database layer**: Create a connection adapter (`DatabasePort` protocol) that wraps either
`aiosqlite.Connection` (SQLite mode) or an `asyncpg` connection (Supabase mode). The adapter
auto-converts `?` parameter placeholders to `$1, $2, ...` for PostgreSQL, and presents the same
cursor-like interface (`execute`, `fetchone`, `fetchall`, `commit`) to all existing service code.
No service files need SQL rewrites — only type annotations change from `aiosqlite.Connection` to
`DatabasePort`.

**Search**: FTS5 (SQLite) and `tsvector`/`tsquery` (PostgreSQL) are incompatible. The search
service implements dual query paths selected by adapter type.

**Auth**: In Supabase mode, Supabase Auth issues JWTs. The backend validates these against
`SUPABASE_JWT_SECRET` and looks up user roles from a `profiles` table (linked to `auth.users`).
Custom login/refresh/setup endpoints are disabled. User creation is handled exclusively via the
Supabase Dashboard (no in-app user creation UI in Supabase mode).

**Backend hosting**: FastAPI is wrapped with Mangum to run as a Netlify Function (AWS Lambda
compatible ASGI adapter). All `/api/*` and `/health` routes redirect to the function.

**Frontend hosting**: SvelteKit is built with `@sveltejs/adapter-netlify` when the `NETLIFY`
environment variable is set (as Netlify injects it automatically); otherwise `adapter-auto` is used
(preserving local development).

**Audit log**: In Supabase mode, the audit log moves from a separate `iris_audit.db` file to an
`audit_log` table in the same PostgreSQL database. The hash-chain integrity mechanism is preserved
— the implementation is identical, just on a different storage backend.

## Options Considered

**A. Full Repository Pattern (rejected)**: Extract all SQL into typed repository classes with
SQLite and PostgreSQL implementations. Clean architecture but requires touching every service
function body — estimated 3,000+ lines of churn across 30 files with no user-visible benefit.

**B. SQL dialect translator (rejected)**: Parse and rewrite SQL queries at runtime (replace `?`
with `$N`, `datetime('now')` with `NOW()`, etc.). Brittle and untestable; edge cases in SQL
translation are unpredictable.

**C. Connection Adapter (chosen)**: Thin wrapper that normalises the driver interface without
changing query strings. `?` → `$N` conversion is mechanical and safe. Service code is unchanged
except type annotations. Dual implementations only where truly needed (FTS5 vs tsvector).

## Consequences

- SQLite deployment is unchanged; all 556 existing tests continue to pass without modification
- Supabase mode requires a `SUPABASE_DB_URL` (PostgreSQL connection string) and Supabase project
- User creation in Supabase mode requires the Supabase Dashboard — no in-app signup or admin
  user-creation flow; this is acceptable and must be clearly documented
- Netlify Functions have cold-start latency and a 26-second timeout; not suitable for long-running
  operations (large imports, thumbnail regeneration) — these remain dev/on-prem features
- The `cairosvg` dependency (thumbnail generation) may not be available in the Netlify Function
  runtime; thumbnails are disabled in Supabase mode at startup
- FTS5 search is replaced by PostgreSQL full-text search in Supabase mode; relevance ranking
  differs slightly but functional parity is maintained
- Adding a new service in future requires type annotation `db: DatabasePort` (not `aiosqlite.Connection`)
