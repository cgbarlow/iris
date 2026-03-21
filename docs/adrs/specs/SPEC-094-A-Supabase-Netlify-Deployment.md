# SPEC-094-A: Optional Supabase/Netlify Deployment

**ADR:** [ADR-094](../ADR-094-Optional-Supabase-Netlify-Deployment.md)
**Status:** Implemented

## Overview

Implements the Supabase/Netlify optional deployment mode. The deployment mode is selected via
`IRIS_DB_BACKEND` environment variable (`sqlite` = default, `supabase` = cloud).

## Configuration

### New environment variables (Supabase mode only)

| Variable | Description |
|----------|-------------|
| `IRIS_DB_BACKEND` | `sqlite` (default) or `supabase` |
| `SUPABASE_URL` | Supabase project URL (`https://<ref>.supabase.co`) |
| `SUPABASE_ANON_KEY` | Supabase anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (backend only) |
| `SUPABASE_DB_URL` | PostgreSQL connection string (`postgresql://...`) |
| `SUPABASE_JWT_SECRET` | JWT secret from Supabase project settings |

### Backend config additions (`backend/app/config.py`)

```python
@dataclass(frozen=True)
class SupabaseConfig:
    url: str
    anon_key: str
    service_role_key: str
    db_url: str
    jwt_secret: str

# Added to AppConfig:
db_backend: str  # "sqlite" | "supabase"
supabase: SupabaseConfig | None  # None when db_backend == "sqlite"
```

### Frontend config (`frontend/src/lib/config.ts`)

```typescript
export const DB_BACKEND: string        // VITE_DB_BACKEND (default "sqlite")
export const SUPABASE_URL: string      // VITE_SUPABASE_URL
export const SUPABASE_ANON_KEY: string // VITE_SUPABASE_ANON_KEY
```

## Database Adapter (`backend/app/db/adapter.py`)

### `DatabasePort` Protocol

Defines the interface all service code uses. Both adapters implement this protocol.

```python
class DatabasePort(Protocol):
    async def execute(self, query: str, params: tuple[Any, ...] = ()) -> AsyncCursor: ...
    async def commit(self) -> None: ...
```

### `AsyncCursor` Protocol

Returned by `execute()`, providing the same fetch interface as `aiosqlite.Cursor`.

```python
class AsyncCursor(Protocol):
    async def fetchone(self) -> Row | None: ...
    async def fetchall(self) -> list[Row]: ...
    @property
    def lastrowid(self) -> int | None: ...
```

### `SqliteAdapter`

Thin wrapper around `aiosqlite.Connection`. Passes all calls through unchanged.

### `SupabaseAdapter`

Wraps an `asyncpg` connection pool. On each `execute()`:
1. Convert `?` placeholders to `$1, $2, ...`
2. Execute via asyncpg connection acquired from pool
3. Wrap result in `AsyncpgCursor` (implements `AsyncCursor`)
4. `commit()` is a no-op (asyncpg uses autocommit by default; DML statements commit immediately)

## Database Manager (`backend/app/database.py`)

`DatabaseManager` becomes backend-aware:

- **SQLite mode**: existing behaviour — two `aiosqlite.Connection` instances wrapped in `SqliteAdapter`
- **Supabase mode**: creates `asyncpg` connection pool; `main_db` and `audit_db` both return
  `SupabaseAdapter` instances pointing to the same PostgreSQL database (the audit log uses a
  separate table, not a separate database)

## PostgreSQL Migrations (`backend/app/migrations/supabase/`)

One SQL file per SQLite migration (m001 through m026), plus `m027_profiles.sql`.

Key PostgreSQL adaptations:
- `INTEGER NOT NULL DEFAULT 0/1` booleans → `BOOLEAN NOT NULL DEFAULT FALSE/TRUE`
- `datetime('now')` → `NOW()`
- `TEXT NOT NULL DEFAULT (lower(hex(randomblob(4)))||...)` UUIDs → `gen_random_uuid()`
- FTS5 virtual tables → regular tables with `tsvector` column + GIN index + trigger for auto-update
- Audit log in the main database (not a separate file)
- `PRAGMA` statements omitted (no equivalent in PostgreSQL)
- `executescript` replaced by individual statements

### Profiles table (`m027_profiles.sql`)

```sql
CREATE TABLE IF NOT EXISTS profiles (
    id           UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username     TEXT        NOT NULL UNIQUE,
    role         TEXT        NOT NULL DEFAULT 'viewer' REFERENCES roles(id),
    is_active    BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Auto-create profile stub on new Supabase auth user (populated by admin post-creation)
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    INSERT INTO profiles (id, username, role)
    VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'username', NEW.email), 'viewer')
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();
```

## Startup (`backend/app/startup.py`)

Branches on `config.db_backend`:

- **SQLite**: existing flow (unchanged)
- **Supabase**: run PostgreSQL migrations (idempotent `CREATE TABLE IF NOT EXISTS`), skip PRAGMA
  config, skip FTS5 rebuild (tsvector columns use triggers), skip thumbnail regeneration

## Search Service (`backend/app/search/service.py`)

Detects `SupabaseAdapter` at runtime:

- **SQLite**: existing FTS5 `MATCH` queries
- **Supabase**: `to_tsvector` / `to_tsquery` queries against `tsvector` columns

## Auth (`backend/app/auth/`)

### `supabase_service.py` (new)

```python
def decode_supabase_jwt(token: str, jwt_secret: str) -> dict[str, Any]:
    """Validate a Supabase-issued JWT and return its payload."""
```

Supabase JWTs use HS256 with the project's JWT secret. The payload contains `sub` (user UUID),
`role` (Supabase role — usually `"authenticated"`), `iat`, `exp`.

### `dependencies.py` changes

`get_current_user` branches on `config.db_backend`:

- **SQLite**: existing flow (decode custom JWT, look up `users` table)
- **Supabase**: decode Supabase JWT, look up `profiles` table by UUID `sub`, return role from profile

### `router.py` changes

- Supabase mode: login, refresh, setup, change-password routes are **not registered**
- Both modes: `GET /api/auth/me` returns current user info (used by frontend to bootstrap session)

## Users Router (`backend/app/users/router.py`)

- **SQLite**: unchanged
- **Supabase**: `list_users` reads from `profiles`, `create_user` returns `HTTP 501 Not Implemented`
  with message directing admin to Supabase Dashboard, `update_user` updates `profiles`

## Audit Middleware (`backend/app/middleware/audit.py`)

Handles Supabase JWT claim differences:
- `sub` is a UUID string (not a short UUID as in SQLite mode)
- Username resolved from `profiles.username` (not `users.username`)

## Frontend

### `frontend/src/lib/config.ts` (new)

```typescript
export const DB_BACKEND = import.meta.env.VITE_DB_BACKEND ?? 'sqlite';
export const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL ?? '';
export const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY ?? '';
```

### `frontend/src/lib/supabase.ts` (new)

```typescript
import { createClient } from '@supabase/supabase-js';
import { SUPABASE_URL, SUPABASE_ANON_KEY } from './config';
export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
```
(Only instantiated when `DB_BACKEND === 'supabase'`)

### `frontend/src/lib/stores/auth.svelte.ts`

Dual-mode auth store:
- **SQLite mode**: existing sessionStorage-based JWT store (unchanged)
- **Supabase mode**: wraps `supabase.auth.getSession()` and `onAuthStateChange`; exports the same
  interface (`getAccessToken`, `getCurrentUser`, `isAuthenticated`, `setAuth`, `clearAuth`)

### `frontend/src/lib/utils/api.ts`

In Supabase mode, retrieves access token from Supabase session instead of custom JWT store.
The `apiFetch` function interface is unchanged.

### `frontend/src/routes/login/+page.svelte`

- **SQLite mode**: existing login UI (unchanged)
- **Supabase mode**: calls `supabase.auth.signInWithPassword()`; setup/request-account views
  are hidden (not applicable in Supabase mode)

### `frontend/svelte.config.js`

```javascript
import adapterAuto from '@sveltejs/adapter-auto';
import adapterNetlify from '@sveltejs/adapter-netlify';

const adapter = process.env.NETLIFY ? adapterNetlify() : adapterAuto();
```

## Netlify Deployment

### `netlify.toml`

```toml
[build]
  command = "cd frontend && npm ci && npm run build"
  publish = "frontend/build"
  functions = "netlify/functions"

[functions]
  included_files = ["backend/**"]

[[redirects]]
  from = "/api/*"
  to = "/.netlify/functions/api/:splat"
  status = 200

[[redirects]]
  from = "/health"
  to = "/.netlify/functions/api"
  status = 200

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

### `netlify/functions/api.py`

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))
from mangum import Mangum
from app.main import create_app
handler = Mangum(create_app(), lifespan="auto")
```

## User Creation (Supabase Mode)

Users must be created via the **Supabase Dashboard**:

1. In the Supabase Dashboard → Authentication → Users → "Invite user"
2. Enter the user's email; Supabase sends an invite email
3. After the user accepts, navigate to the `profiles` table in the Supabase Table Editor
4. Find the auto-created profile row and set `role` to the desired Iris role
   (`viewer`, `reviewer`, `architect`, or `admin`)
5. The user can now log in at the Iris Netlify URL

Full deployment instructions: `docs/deployment-netlify-supabase.md`

## Files

### New files
- `docs/adrs/ADR-094-Optional-Supabase-Netlify-Deployment.md`
- `docs/adrs/specs/SPEC-094-A-Supabase-Netlify-Deployment.md`
- `backend/app/db/__init__.py`
- `backend/app/db/adapter.py`
- `backend/app/auth/supabase_service.py`
- `backend/app/migrations/supabase/` (27 SQL files)
- `netlify.toml`
- `netlify/functions/api.py`
- `netlify/functions/requirements.txt`
- `frontend/src/lib/config.ts`
- `frontend/src/lib/supabase.ts`
- `docs/deployment-netlify-supabase.md`
- `.env.example`

### Modified files
- `backend/app/config.py` — add SupabaseConfig, db_backend
- `backend/app/database.py` — backend-aware DatabaseManager
- `backend/app/startup.py` — conditional init
- `backend/app/auth/dependencies.py` — dual auth validation
- `backend/app/auth/router.py` — conditional route registration
- `backend/app/users/router.py` — profiles support in Supabase mode
- `backend/app/search/service.py` — dual search
- `backend/app/middleware/audit.py` — Supabase JWT claims
- `backend/pyproject.toml` — add mangum, asyncpg optional deps
- `frontend/package.json` — add adapter-netlify, supabase-js
- `frontend/svelte.config.js` — conditional adapter
- `frontend/src/lib/stores/auth.svelte.ts` — dual auth store
- `frontend/src/lib/utils/api.ts` — dual token source
- `frontend/src/routes/login/+page.svelte` — dual login UI
- `README.md` — document deployment options
- `CHANGELOG.md` — new version entry
