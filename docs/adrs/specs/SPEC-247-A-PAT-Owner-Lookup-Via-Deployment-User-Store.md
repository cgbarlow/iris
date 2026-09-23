# SPEC-247-A: Resolve a PAT's Owner Through the Deployment's User Store

Implements **[ADR-247](../ADR-247-PAT-Owner-Lookup-Via-Deployment-User-Store.md)**.
Amends the verification step of [SPEC-127-A](./SPEC-127-A-Personal-Access-Tokens.md).

## 1. Root cause

`verify_pat` fetched the PAT and its owner in one query:

```sql
SELECT pat.id, pat.user_id, pat.token_hash, pat.revoked_at, pat.expires_at,
       u.username, u.role, u.is_active
FROM personal_access_tokens pat
JOIN users u ON u.id = pat.user_id
WHERE pat.prefix = ?
```

| Deployment | `users.id` | `personal_access_tokens.user_id` | Result |
|------------|-----------|----------------------------------|--------|
| SQLite | `TEXT` | `TEXT` → `users(id)` (m041) | works |
| Supabase | `TEXT` (startup mirror of `profiles`) | `UUID` → `profiles(id)` (m042) | `UndefinedFunctionError: operator does not exist: text = uuid` → 500 |

Reproduced against PostgreSQL 16 with the real Supabase migrations applied;
matches the UAT `iris-api` log for every PAT request.

## 2. Changes

| File | Change |
|------|--------|
| `backend/app/auth/users.py` | New. `get_user(db, user_id, db_backend) -> {id, username, role, is_active} \| None`. Supabase: delegates to `supabase_service.get_profile` (`profiles`). SQLite: `SELECT id, username, role, is_active FROM users WHERE id = ?`. |
| `backend/app/tokens/service.py` | `verify_pat(db, token, hasher, db_backend="sqlite")`. The PAT row is read without a join; after the revoked/expired checks the owner is resolved with `get_user`, and a missing or inactive owner is rejected (→ `None`). The returned user dict takes `id`/`username`/`role` from `get_user`. |
| `backend/app/auth/dependencies.py` | `_get_current_user_pat` passes `request.app.state.config.db_backend`. `_get_current_user_sqlite` uses `get_user(db, user_id, "sqlite")` in place of its inline `users` query. |

Rejection order is unchanged apart from the owner check moving after the
revoked/expired checks: malformed → unknown prefix → revoked → expired →
missing/inactive owner → hash mismatch. Every rejection still returns
`None` (→ 401), so the order is not observable to callers.

## 3. Tests (TDD)

`backend/tests/test_tokens/test_verify_pat_postgres.py` (new). Each test
creates a fresh PostgreSQL database, applies a stub of Supabase's `auth`
schema (`auth.users`, `auth.uid()`) plus the real `m001_roles_users.sql`,
`m027_profiles.sql` and `m042_personal_access_tokens.sql`, and drops the
database afterwards. Runs when `IRIS_TEST_POSTGRES_DSN` is set; skipped
otherwise.

Red before the change: the same assertions against the old `verify_pat`
raised `asyncpg.exceptions.UndefinedFunctionError: operator does not exist:
text = uuid`. Green after:

1. `test_happy_path` — profile mirrored into `users` (the UAT state): PAT
   verifies; returns the profile's id, username and role, `auth_type="pat"`,
   `jti` = PAT id.
2. `test_profile_not_yet_mirrored_into_users` — a profile with no `users`
   row still verifies.
3. `test_role_comes_from_profiles` — role changed in `profiles` after the
   mirror was taken → the new role is returned.
4. `test_inactive_profile_rejected` — `profiles.is_active = FALSE` → `None`.
5. `test_touches_last_used_at` — `last_used_at` is set after a successful
   verification.
6. `TestBearerPatOnSupabaseDeployment::test_get_current_user_accepts_pat` —
   `get_current_user` with `config.db_backend="supabase"` and a PAT bearer
   returns the profile user (the request path passes the backend through).

The existing SQLite suites (`tests/test_tokens/test_service.py`,
`test_routes.py`, `tests/test_auth/`) cover the SQLite path unchanged and
stay green.

Run locally:

```bash
docker run -d --name iris-test-pg -e POSTGRES_PASSWORD=iris -p 55499:5432 postgres:16-alpine
cd backend
IRIS_TEST_POSTGRES_DSN=postgresql://postgres:iris@localhost:55499/postgres \
  uv run pytest tests/test_tokens/test_verify_pat_postgres.py
```

## 4. Acceptance criteria

- A PAT issued on a Supabase deployment authenticates API requests (no 500).
- The PAT's user, role and active status match what a Supabase JWT for the
  same user resolves to (`profiles`).
- SQLite behaviour is unchanged.
