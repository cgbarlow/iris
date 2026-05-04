# SPEC-127-A: Personal Access Tokens

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-127-A |
| **ADR** | [ADR-127](../ADR-127-Personal-Access-Tokens.md) |
| **Status** | Proposed |
| **Date** | 2026-04-22 |

## Overview

Long-lived revocable bearer tokens for CLI / MCP / agent use. Issued
as `iris_pat_<prefix>_<secret>`, hashed with Argon2id, scoped to the
creating user's existing role. Recognised by the existing auth
dependency alongside JWTs.

## Backend

### Schema (SQLite)

New migration `backend/app/migrations/NNN_add_personal_access_tokens.py`:

```sql
CREATE TABLE personal_access_tokens (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  token_hash TEXT NOT NULL,
  prefix TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_used_at TIMESTAMP,
  expires_at TIMESTAMP,
  revoked_at TIMESTAMP
);
CREATE INDEX idx_pat_prefix ON personal_access_tokens(prefix);
CREATE INDEX idx_pat_user ON personal_access_tokens(user_id);
```

### Schema (Supabase / Postgres)

Mirror table in the Supabase migration with Row Level Security
(per ADR-095):

```sql
CREATE TABLE personal_access_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  token_hash TEXT NOT NULL,
  prefix TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_used_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ
);
CREATE INDEX idx_pat_prefix ON personal_access_tokens(prefix);

ALTER TABLE personal_access_tokens ENABLE ROW LEVEL SECURITY;
-- Owner-only read/write; service role bypasses RLS for server-side lookups.
CREATE POLICY pat_owner_select ON personal_access_tokens
  FOR SELECT USING (user_id = auth.uid());
CREATE POLICY pat_owner_insert ON personal_access_tokens
  FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY pat_owner_update ON personal_access_tokens
  FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY pat_owner_delete ON personal_access_tokens
  FOR DELETE USING (user_id = auth.uid());
```

The backend uses the service-role key for PAT lookup at auth time
(RLS doesn't apply to service role), so anonymous lookup-by-prefix
works without the caller being authenticated.

### Token format

Generated in `backend/app/tokens/service.py`:

```python
TOKEN_PREFIX = "iris_pat_"
PREFIX_LEN = 8  # chars of urlsafe random

def generate_token() -> tuple[str, str, str]:
    """Return (full_token, prefix, hash)."""
    secret = secrets.token_urlsafe(32)  # ~43 chars
    prefix = secrets.token_urlsafe(PREFIX_LEN)[:PREFIX_LEN]
    full = f"{TOKEN_PREFIX}{prefix}_{secret}"
    hash_ = argon2_hasher.hash(secret)
    return full, prefix, hash_
```

- The **full token** is shown to the user exactly once (API response
  on create) and never stored.
- The **prefix** is stored and indexed — used to look up the hash for
  verification (constant-time prefix match + Argon2id verify of the
  secret).
- The **hash** uses the existing `argon2_hasher` from `auth/service.py`
  (same parameters as password hashing — NZISM compliant).

### Auth dependency extension

Modify `backend/app/auth/dependencies.py`:

```python
from app.tokens.service import verify_pat

PAT_PREFIX = "iris_pat_"

async def get_current_user(request: Request) -> dict[str, Any]:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header[len("Bearer "):]

    if token.startswith(PAT_PREFIX):
        return await _get_current_user_pat(request, token)

    config = request.app.state.config
    if config.db_backend == "supabase":
        return await _get_current_user_supabase(request, token)
    return await _get_current_user_sqlite(request, token)


async def _get_current_user_pat(request: Request, token: str) -> dict[str, Any]:
    db = request.app.state.db_manager.main_db
    user = await verify_pat(db, token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or revoked token")
    return user
```

`verify_pat(db, token)`:
1. Parse `iris_pat_<prefix>_<secret>` — reject if malformed (401).
2. Look up `personal_access_tokens` row by `prefix`.
3. Reject if `revoked_at IS NOT NULL` or `expires_at <= now()`.
4. Argon2id verify of the secret against `token_hash`.
5. Join to `users` (SQLite) or `profiles` (Supabase) to fetch the role.
6. Reject if user is inactive.
7. `UPDATE personal_access_tokens SET last_used_at = now() WHERE id = ?`.
8. Return `{"id": user_id, "username": ..., "role": ..., "jti": pat_id}`.

`get_optional_user` is unchanged — it simply calls `get_current_user`
when an `Authorization` header is present, so the PAT path is reached
transparently.

### Rate-limit bucket

Extend `backend/app/middleware/rate_limit.py`:

```python
def _get_rate_category(request: Request) -> str:
    path = request.url.path
    if path == "/api/auth/login":
        return "login"
    if path == "/api/auth/refresh":
        return "refresh"
    auth = request.headers.get("Authorization", "")
    is_anon = not auth
    if path.startswith("/api/ai/") and is_anon:
        return "anon_ai"
    if auth.startswith("Bearer iris_pat_"):
        return "pat"
    if is_anon:
        return "anon"
    return "general"
```

Config defaults (tunable via env per deployment):

| Bucket | Default | Window |
|---|---|---|
| `login` | 5 | 60s |
| `refresh` | 30 | 60s |
| `anon` | 30 | 60s |
| `anon_ai` | 10 | 3600s |
| `pat` | 60 | 60s |
| `general` | 100 | 60s |

### Management endpoints

New router `backend/app/tokens/router.py`, mounted at
`/api/users/me/tokens`:

| Method | Path | Behaviour |
|---|---|---|
| `GET` | `/api/users/me/tokens` | List caller's tokens. Fields: `id`, `name`, `prefix`, `created_at`, `last_used_at`, `expires_at`, `revoked_at`. Secret never returned. |
| `POST` | `/api/users/me/tokens` | Body: `{"name": str, "expires_at": ISO8601 \| null}`. Response: `{"id", "name", "prefix", "created_at", "token"}` — the `token` field is present **only on the create response**. |
| `DELETE` | `/api/users/me/tokens/{id}` | Soft-revoke: `UPDATE SET revoked_at = now()`. Returns 204. Idempotent on already-revoked tokens. |

Auth: `Depends(get_current_user)`. A PAT can manage the PATs of the
same user (PAT-inherits-user-role means a PAT with Architect role can
create another Architect PAT for the same user; this is acceptable
and matches how GitHub PATs work).

Audit log entries are emitted for `create` and `revoke` via the
existing audit infrastructure, with `action="pat_created"` /
`"pat_revoked"` and `target=pat_id`.

### Config additions

`backend/app/config.py`:

```python
@dataclass
class RateLimitConfig:
    login: int = 5
    refresh: int = 30
    anon: int = 30
    anon_ai: int = 10
    pat: int = 60
    general: int = 100
    window_seconds: int = 60
    anon_ai_window_seconds: int = 3600
```

All fields overridable via env (`RATE_LIMIT_PAT`, etc.).

## Frontend

New Settings tab **API Tokens** at `/settings/tokens`
(`frontend/src/routes/settings/tokens/+page.svelte`):

- **List view**: table of existing tokens — columns `Name`, `Prefix`
  (`iris_pat_abc12345…`), `Last used`, `Created`, `Expires`, `Status`
  (Active / Revoked / Expired), `Actions` (Revoke button).
- **Create dialog**: fields `Name` (required), `Expires at` (optional
  date picker). On submit, shows the generated token in a one-shot
  panel with a **Copy** button and a warning (`This secret will not
  be shown again`). Dialog is not dismissable until the user confirms
  they've copied it. After confirmation, the list refreshes.
- **Revoke dialog**: confirm modal (`This cannot be undone. Revoking
  will immediately invalidate any process using this token`).
- Accessibility: WCAG 2.2 AA (matches `/settings/*` pattern), 24px
  touch targets, focus management on the copy-dialog.
- Security: the token secret is never written to the Svelte store
  beyond the create-dialog scope; on close it's garbage-collected.

## Testing (TDD)

Red-green-refactor; tests written before implementation.

### Backend unit tests

`backend/tests/test_tokens.py`:

- `test_generate_token_format` — returned token matches
  `iris_pat_<8>_<…>`; hash verifies; prefix is lookupable.
- `test_verify_pat_happy_path` — create, then `verify_pat()` returns
  the expected user dict.
- `test_verify_pat_wrong_secret` — returns None.
- `test_verify_pat_revoked` — returns None, updates nothing.
- `test_verify_pat_expired` — returns None.
- `test_verify_pat_inactive_user` — returns None.
- `test_verify_pat_touches_last_used_at` — after verify, the row's
  `last_used_at` is within 1s of now.

`backend/tests/test_auth_dependencies.py`:

- `test_pat_routes_to_pat_validator` — Bearer `iris_pat_...` ends up
  in `_get_current_user_pat`.
- `test_jwt_routes_to_jwt_validator` — unchanged path still works.
- `test_invalid_pat_returns_401`.

`backend/tests/test_rate_limit.py`:

- `test_pat_category_for_pat_bearer` — header with `iris_pat_` maps
  to `pat` bucket.
- `test_anon_ai_category_retained` — `anon_ai` still triggers for
  anonymous AI endpoints.
- `test_buckets_independent` — PAT traffic does not consume the
  `general` bucket.

`backend/tests/test_tokens_router.py`:

- POST create returns the secret; GET list hides it.
- DELETE revokes; subsequent GET shows `revoked_at` set.
- Caller-scoped: user A's PAT cannot list/revoke user B's PATs (404).
- Audit log entries emitted.

### Frontend tests

- Vitest unit test for the create-dialog's one-shot behaviour (token
  cleared on close).
- Playwright BDD: `tokens-management.feature` — login, create, copy,
  revoke.

## Acceptance criteria

1. `POST /api/users/me/tokens` returns a token matching
   `/^iris_pat_[A-Za-z0-9_-]{8}_[A-Za-z0-9_-]{43}$/` exactly once.
2. `curl -H "Authorization: Bearer iris_pat_..." /api/search?q=foo`
   returns 200.
3. Revoking a PAT → next request with that PAT returns 401.
4. A PAT inherits the user's role (verified by an Architect PAT
   passing a `require_permission("create_model")` endpoint and a
   Viewer PAT failing it).
5. Rate-limit: PATs and JWTs do not share a bucket — a JWT user
   hitting its limit does not lock out PAT users.
6. Frontend: Settings → API Tokens renders the list, create dialog,
   and revoke confirm; E2E BDD passes.
7. No `{@html}` usage in the new frontend code (per protocol 7).
