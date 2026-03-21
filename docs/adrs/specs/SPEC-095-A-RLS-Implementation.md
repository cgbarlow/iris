# SPEC-095-A: Row Level Security Implementation

**ADR:** ADR-095 (Row Level Security for Supabase Tables)
**Status:** Complete

## Overview

Migration `m030_rls_policies.sql` enables PostgreSQL Row Level Security on all 34 Supabase tables
using a deny-all strategy (RLS enabled, no policies). This blocks the `anon` and `authenticated`
roles from accessing any table via the Supabase REST API while the `postgres` role (FastAPI backend)
bypasses RLS as table owner.

## Tables (34)

All tables created by Supabase migrations m001–m029:

| # | Table | Source Migration | Purpose |
|---|-------|-----------------|---------|
| 1 | `roles` | m001 | RBAC role definitions |
| 2 | `role_permissions` | m001 | Role-to-permission mappings |
| 3 | `users` | m001 | User accounts (SQLite mode) |
| 4 | `password_history` | m001 | Password reuse prevention |
| 5 | `refresh_tokens` | m001 | JWT refresh token storage |
| 6 | `sets` | m002 | Top-level content containers |
| 7 | `packages` | m002 | Package hierarchy nodes |
| 8 | `package_versions` | m002 | Package version history |
| 9 | `elements` | m002 | Architectural entities |
| 10 | `element_versions` | m002 | Element version history |
| 11 | `relationships` | m002 | Entity-to-entity relationships |
| 12 | `relationship_versions` | m002 | Relationship version history |
| 13 | `diagrams` | m002 | Diagram definitions |
| 14 | `diagram_versions` | m002 | Diagram version history |
| 15 | `audit_log` | m003 | SHA-256 hash-chained audit trail |
| 16 | `comments` | m004 | User comments on entities |
| 17 | `bookmarks` | m004 | User bookmarks |
| 18 | `settings` | m006 | Application settings key-value store |
| 19 | `diagram_thumbnails` | m007 | PNG thumbnail cache |
| 20 | `element_tags` | m008 | Element tag associations |
| 21 | `diagram_tags` | m009 | Diagram tag associations |
| 22 | `package_relationships` | m015 | Cross-package relationships |
| 23 | `views` | m017 | Saved view definitions |
| 24 | `diagram_types` | m020 | Diagram type registry |
| 25 | `notations` | m020 | Notation registry (UML, ArchiMate, etc.) |
| 26 | `diagram_type_notations` | m020 | Notation-to-diagram-type mappings |
| 27 | `edit_locks` | m021 | Optimistic edit locking |
| 28 | `themes` | m024 | Visual theme configurations |
| 29 | `diagram_links` | m025 | Inter-diagram navigation links |
| 30 | `ai_providers` | m026 | AI provider registry (API keys, endpoints) |
| 31 | `ai_conversations` | m026 | AI conversation history |
| 32 | `ai_usage_log` | m026 | AI API usage tracking |
| 33 | `profiles` | m027 | Supabase auth user profiles |
| 34 | `ai_creation_prompts` | m029 | Layered AI diagram creation prompts |

## Why no policies

Policies are not needed because:

1. **Backend access** — The FastAPI backend connects as `postgres` (table owner), which
   automatically bypasses RLS. No policy is needed for backend operations.

2. **No frontend table queries** — The Supabase JS client in the frontend is used exclusively for
   authentication (`signInWithPassword`, `refreshSession`, `signOut`). All data operations go
   through the FastAPI API (`/api/*` routes), which the backend handles with full RBAC.

3. **service_role bypass** — The `service_role` key (used only server-side) also bypasses RLS.
   This key is never exposed to the frontend.

Adding policies would only be necessary if the frontend needed to query tables directly via
`supabase.from('table').select()` — which is explicitly not part of Iris's architecture.

## PostgreSQL role behaviour with RLS

| Role | How it connects | RLS behaviour | Used by |
|------|----------------|---------------|---------|
| `postgres` | asyncpg (backend) | **Bypasses** RLS (table owner) | FastAPI API |
| `service_role` | Supabase admin SDK | **Bypasses** RLS | Server-side admin scripts |
| `authenticated` | Supabase JS (logged-in) | **Blocked** (no policies) | Not used for table queries |
| `anon` | Supabase JS (not logged-in) | **Blocked** (no policies) | Auth only |

## Migration details

**File:** `backend/app/migrations/supabase/m030_rls_policies.sql`

- 34 `ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;` statements
- Idempotent: PostgreSQL ignores `ENABLE ROW LEVEL SECURITY` if already enabled
- No `FORCE ROW LEVEL SECURITY` — table owner must bypass RLS
- Executed automatically by `run_supabase_migrations()` (alphabetical file discovery)

## Test coverage

**File:** `backend/tests/test_migrations/test_rls_policies.py`

| Test | Validates |
|------|-----------|
| `test_rls_migration_file_exists` | m030_rls_policies.sql exists in migrations directory |
| `test_every_table_has_rls` | Every `CREATE TABLE` in m001–m029 has a matching `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` in m030 |
| `test_no_extra_rls_tables` | m030 does not reference tables that don't exist in m001–m029 |

These are structural validation tests (the SQLite test environment cannot test actual PostgreSQL
RLS enforcement). They ensure that when new tables are added to future migrations, the developer
is reminded to add RLS coverage.

## Manual verification

After applying m030 to a Supabase instance:

```bash
# Should return [] (empty array) — RLS blocks anon access
curl "https://<project>.supabase.co/rest/v1/users?select=*" \
  -H "apikey: <anon-key>" \
  -H "Authorization: Bearer <anon-key>"

# Backend CRUD should still work (connects as postgres, bypasses RLS)
curl "https://<netlify-site>.netlify.app/api/auth/me" \
  -H "Authorization: Bearer <valid-jwt>"
```
