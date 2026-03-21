# ADR-095: Row Level Security for Supabase Tables

**Status:** Accepted
**Date:** 2026-03-21
**Depends on:** ADR-094 (Supabase/Netlify Deployment)

## Context

The Supabase deployment mode (ADR-094) embeds the Supabase `anon` key in the frontend bundle
(`VITE_SUPABASE_ANON_KEY`). This key is intentionally public — Supabase's security model relies on
**Row Level Security (RLS)** to restrict what the `anon` and `authenticated` roles can access.

Without RLS enabled, the `anon` key can be used to query **all tables** directly via the Supabase
PostgREST REST API (`https://<project>.supabase.co/rest/v1/<table>`), completely bypassing Iris's
authentication and RBAC checks. This is a critical security gap: any user with the `anon` key
(visible in the page source) could read, insert, update, or delete rows in any table.

Iris's architecture routes all data access through the FastAPI backend, which connects as the
`postgres` role (table owner) via asyncpg. The frontend Supabase JS client is used **only** for
authentication (sign-in, token refresh, sign-out) — never for direct table queries.

## Decision

Enable PostgreSQL Row Level Security on **every table** created by Supabase migrations m001–m029
(34 tables total) using a **deny-all** strategy: RLS is enabled with **no policies**.

### How deny-all works

When RLS is enabled on a table with no policies:
- **`anon` role** (browser via Supabase JS): **DENIED** all access (SELECT, INSERT, UPDATE, DELETE)
- **`authenticated` role** (logged-in user via Supabase JS): **DENIED** all access
- **`postgres` role** (table owner, FastAPI backend via asyncpg): **BYPASSES** RLS automatically
- **`service_role`** (Supabase admin key, server-only): **BYPASSES** RLS automatically

This is the correct strategy because:
1. The backend is the sole data access path — it enforces Iris RBAC at the application layer
2. No frontend code queries tables directly; Supabase JS is auth-only
3. No per-row access distinctions are needed (all-or-nothing access per role)

### Why not FORCE ROW LEVEL SECURITY

`ALTER TABLE ... FORCE ROW LEVEL SECURITY` makes RLS apply even to the table owner. We explicitly
do **not** use this because the FastAPI backend connects as the `postgres` role (table owner) and
must have unrestricted access. FORCE would require creating permissive policies for the backend,
adding complexity with no security benefit.

## Options Considered

**A. Deny-all RLS (chosen):** Enable RLS with no policies. Simplest approach — one `ALTER TABLE`
per table, zero policies to maintain. The backend bypasses RLS as table owner.

**B. Selective RLS with policies:** Enable RLS and create policies granting `authenticated` users
read access to specific tables. Unnecessary because the frontend never queries tables directly.
Would create a maintenance burden (policies must be updated whenever table schemas change).

**C. Revoke PostgREST grants:** Remove `SELECT`/`INSERT`/`UPDATE`/`DELETE` grants from `anon` and
`authenticated` on each table. Fragile — Supabase may re-grant permissions on schema changes or
dashboard actions. RLS is the Supabase-recommended approach.

**D. No action:** Leave tables unprotected. Unacceptable — the `anon` key is in the frontend
bundle and can be used to bypass all Iris security.

## Consequences

### Positive
- Closes the critical security gap: `anon` key can no longer be used for direct table access
- Zero maintenance: no policies to update as tables evolve
- Backend is completely unaffected (table owner bypasses RLS)
- Idempotent migration: `ENABLE ROW LEVEL SECURITY` is a no-op if already enabled
- Structural test ensures future tables are not forgotten

### Negative
- If a future requirement needs direct Supabase JS table access from the frontend, per-table
  policies will need to be added (this is expected and standard Supabase practice)

### Risks
- None identified. The migration is idempotent and cannot break existing data or queries.

## Verification

1. Structural test (`tests/test_migrations/test_rls_policies.py`) verifies every table from
   m001–m029 has a corresponding `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` in m030
2. Manual verification: after applying m030, query any table with the `anon` key via REST —
   should return empty result with no error (PostgREST returns `[]` when RLS denies access)
3. Backend CRUD operations continue to work (backend connects as `postgres`, bypasses RLS)
