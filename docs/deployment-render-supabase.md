# Deploying Iris to Render + Supabase

This guide covers deploying Iris as a static SvelteKit frontend, a Scenia React roadmapping SPA, and a FastAPI backend on **Render**, backed by a **Supabase** PostgreSQL database and Supabase Auth.

> **Default deployment is SQLite (self-hosted).** Render + Supabase is an optional cloud deployment path. See the main README for standard self-hosted setup.

## Prerequisites

- A [Render](https://render.com) account (free tier works)
- A [Supabase](https://supabase.com) account
- The Iris repository cloned locally (or forked on GitHub)

---

## Step 1 — Create a Supabase project

1. Log in to [app.supabase.com](https://app.supabase.com) and click **New project**.
2. Choose an organisation, project name, database password, and region. Save the database password securely.
   > **Do not** check "Enable automatic RLS". Iris manages RLS explicitly via migration `m030_rls_policies.sql` — an automatic trigger could interfere with migration ordering.
3. After the project provisions, go to **Settings → General** and note the **Project ID** (e.g. `onaojeffmvyzajrnuzqj`). The project URL is `https://<project-id>.supabase.co` (`SUPABASE_URL`).
4. Go to **Settings → API Keys** and note:
   - **Publishable key** (default) → use as `SUPABASE_ANON_KEY` / `VITE_SUPABASE_ANON_KEY`
   - **Secret key** (default) → use as `SUPABASE_SERVICE_ROLE_KEY`

   > Supabase now uses **Publishable keys** (`sb_publishable_*`) and **Secret keys** (`sb_secret_*`). These replace the legacy `anon` and `service_role` JWT keys. Both formats work with the Supabase JS SDK. If you see a "Legacy anon, service_role API keys" tab, use the new keys instead.

5. Go to **Settings → API Keys → JWT Settings** (or **Settings → Data API**) and note:
   - **JWT Secret** (`SUPABASE_JWT_SECRET`)
6. Click the **Connect** button (top bar, next to the branch name) to find connection strings. Set **Method** to **Transaction pooler** (port 6543, IPv4 compatible). Copy the URI and replace `[YOUR-PASSWORD]` with your database password — this is your `SUPABASE_DB_URL`.
   > The Transaction pooler does not support PREPARE statements. The Iris backend handles this automatically (`statement_cache_size=0` on the asyncpg pool).

---

## Step 2 — Run the PostgreSQL migrations

All 35 migration files are in `backend/app/migrations/supabase/` (m001–m035). They are idempotent and safe to re-run.

### Option A: Script (recommended)

If you have `psql` installed locally, run all migrations in one command using the **Direct connection** URI (port 5432, not the Transaction pooler):

```sh
./scripts/supabase-migrate.sh "postgresql://postgres:YOUR-PASSWORD@db.xxxx.supabase.co:5432/postgres"
```

### Option B: Supabase SQL Editor

1. Open the **SQL Editor** in your Supabase project.
2. Concatenate all migration files and paste into a single query:

   ```sh
   cat backend/app/migrations/supabase/m*.sql | pbcopy   # macOS
   cat backend/app/migrations/supabase/m*.sql | xclip    # Linux
   ```

3. Paste into the SQL Editor and click **Run**.

### What the migrations do

- **m001–m026**: Core schema (tables, indexes, FTS triggers, seed data)
- **m027**: `profiles` table + trigger that auto-creates a profile row when Supabase Auth creates a user (no manual inserts needed)
- **m028**: DoView notation, diagram types, mappings, and theme (seed data)
- **m029**: `ai_creation_prompts` table + 4 seeded layered prompts
- **m030**: Row Level Security on all 34 tables (see [Verifying Row Level Security](#verifying-row-level-security))

---

## Step 3 — Create the first admin user

Iris users in Supabase mode are managed entirely through the **Supabase Dashboard** — there is no in-app user creation.

1. Go to **Authentication → Users** in the Supabase Dashboard.
2. Click **Invite user** (or **Add user → Create new user**) and enter the admin's email and a temporary password.
3. After the user is created, go to **SQL Editor** and update their profile role to `admin`:

   ```sql
   UPDATE profiles
   SET role = 'admin'
   WHERE username = 'admin@example.com';  -- replace with the email you just created
   ```

   > The `profiles` trigger sets `role = 'viewer'` by default. Update this immediately after creating each admin user.

4. Share the email + temporary password with the admin. They can change their password via the Supabase Auth UI or via the Iris login page (password reset is handled by Supabase — configure email templates in **Authentication → Email Templates**).

### Creating additional users

To add more users after initial setup:

1. **Supabase Dashboard → Authentication → Users → Invite user** (or Add user).
2. Update the `role` in `profiles` via SQL:

   ```sql
   UPDATE profiles SET role = 'architect' WHERE username = 'user@example.com';
   ```

   Available roles: `admin`, `architect`, `reviewer`, `viewer`.

3. To deactivate a user:

   ```sql
   UPDATE profiles SET is_active = FALSE WHERE username = 'user@example.com';
   ```

---

## Step 4 — Deploy to Render

### Option A: Blueprint (recommended)

1. Push your Iris fork/repo to GitHub.
2. Log in to [Render](https://render.com), click **New → Blueprint**.
3. Connect to GitHub and select your Iris repository.
4. Render will detect `render.yaml` and create three services:
   - **iris-frontend** — Static Site serving the SvelteKit SPA
   - **scenia** — Static Site serving the Scenia React roadmapping SPA (from external fork)
   - **iris-api** — Web Service running FastAPI via uvicorn

> **Note:** The `scenia` service uses the `repo` and `branch` fields to build from `cgbarlow/waylonkenning_scenia` (branch `feature/iris-embed`). The Render GitHub integration must have access to this repository.

### Option B: Manual setup

Create three services manually in the Render Dashboard:

**Static Site (frontend):**
- Name: `iris-frontend`
- Build command: `cd frontend && npm ci && npm run build`
- Publish directory: `frontend/build`
- Add rewrite rule: `/* → /index.html` (for SPA client-side routing)

**Static Site (Scenia):**
- Name: `scenia`
- Repository: `cgbarlow/waylonkenning_scenia` (branch `feature/iris-embed`)
- Build command: `npm ci && npm run build`
- Publish directory: `dist`
- Add rewrite rule: `/* → /index.html` (for SPA client-side routing)

**Web Service (backend):**
- Name: `iris-api`
- Runtime: Python
- Build command: `cd backend && pip install -e ".[supabase]"`
- Start command: `cd backend && uvicorn app.main:create_app --host 0.0.0.0 --port $PORT --factory`

---

## Step 5 — Set environment variables in Render

### Frontend (iris-frontend)

| Variable | Value | Description |
|----------|-------|-------------|
| `VITE_DB_BACKEND` | `supabase` | Enables Supabase deployment mode |
| `VITE_SUPABASE_URL` | `https://xxxx.supabase.co` | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | `sb_publishable_...` | Supabase publishable key |
| `VITE_API_BASE_URL` | `https://iris-api.onrender.com` | URL of the iris-api web service |
| `VITE_SCENIA_URL` | `https://scenia.onrender.com` | URL of the Scenia static site |

> **Security note:** `VITE_*` variables are embedded in the frontend bundle at build time and visible to users. Use the **publishable** key (not the secret key) for `VITE_SUPABASE_ANON_KEY`. RLS (m030) prevents the publishable key from accessing any table data directly.

### Scenia (scenia)

| Variable | Value | Description |
|----------|-------|-------------|
| `VITE_API_BASE_URL` | `https://iris-api.onrender.com` | URL of the iris-api web service |

> Scenia receives auth tokens at runtime via URL query parameters from the Iris frontend (see `openScenia()` in `frontend/src/lib/scenia/config.ts`). No Supabase keys are needed at build time.

### Backend (iris-api)

| Variable | Value | Description |
|----------|-------|-------------|
| `IRIS_DB_BACKEND` | `supabase` | Enables Supabase deployment mode |
| `SUPABASE_URL` | `https://xxxx.supabase.co` | Supabase project URL |
| `SUPABASE_ANON_KEY` | `sb_publishable_...` | Supabase publishable key |
| `SUPABASE_SERVICE_ROLE_KEY` | `sb_secret_...` | Supabase secret key (backend only) |
| `SUPABASE_DB_URL` | `postgresql://...` | Transaction pooler connection string |
| `SUPABASE_JWT_SECRET` | `your-jwt-secret` | JWT secret from Supabase settings |
| `IRIS_CORS_ORIGINS` | `https://iris-frontend.onrender.com,https://scenia.onrender.com` | Frontend + Scenia URLs (for CORS) |

> Set `IRIS_CORS_ORIGINS` to your frontend and Scenia Render URLs, comma-separated. Scenia makes cross-origin API calls to the backend.

---

## Step 6 — Verify the deployment

1. Visit your frontend Render URL — you should see the Iris login page.
2. Log in with the admin credentials created in Step 3.
3. Create a model, add entities — verify CRUD operations work.

### Verify CORS

If API calls fail with CORS errors, check that `IRIS_CORS_ORIGINS` on the backend service matches your frontend URL exactly (including `https://`).

---

## Architecture overview

```
Browser
  ↓  HTTPS
Render Static Site (frontend/build — SvelteKit SPA)
  ↓  window.open (new tab, passes JWT + API URL as query params)
Render Static Site (dist — Scenia React SPA)
  ↓  fetch (cross-origin, Bearer token)
Render Web Service (backend — FastAPI via uvicorn)
  ↓  asyncpg (statement_cache_size=0)
Supabase PostgreSQL (Transaction Pooler, port 6543)

Supabase Auth
  ↑  JWT (HS256, SUPABASE_JWT_SECRET)
  ↑  signInWithPassword
Browser (Supabase JS SDK)
```

### Authentication flow

1. User enters **email + password** on the login page.
2. Frontend calls `supabase.auth.signInWithPassword()` — Supabase validates credentials and returns a JWT.
3. Frontend calls `GET /api/auth/me` with the JWT in `Authorization: Bearer <token>`.
4. Backend decodes the JWT using `SUPABASE_JWT_SECRET`, looks up the user's role in the `profiles` table, and returns the user profile.
5. Subsequent API calls include the JWT; backend validates it on every request.
6. Supabase SDK auto-refreshes tokens before expiry; `onAuthStateChange` keeps the frontend store in sync.

---

## Verifying Row Level Security

Migration `m030_rls_policies.sql` enables Row Level Security (RLS) on all 34 tables using a **deny-all** strategy — no policies are created. This means:

- The `anon` key (embedded in the frontend) **cannot** query tables via the Supabase REST API
- The `authenticated` role (logged-in Supabase JS users) **cannot** query tables directly
- The `postgres` role (FastAPI backend via asyncpg) **bypasses** RLS as table owner
- The `service_role` key (server-only) **bypasses** RLS

### Quick verification

After running all migrations, test that RLS is active:

```sql
-- In Supabase SQL Editor: check RLS is enabled on all tables
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

Every table should show `rowsecurity = true`.

### REST API verification

```bash
# This should return an empty array [] — RLS blocks anon access
curl "https://<project>.supabase.co/rest/v1/users?select=*" \
  -H "apikey: <your-anon-key>" \
  -H "Authorization: Bearer <your-anon-key>"
```

If you get data back instead of `[]`, RLS is not enabled — re-run `m030_rls_policies.sql`.

> **See also:** [ADR-095](adrs/ADR-095-Row-Level-Security.md) for the full security rationale.

---

## Limitations and differences from SQLite mode

| Feature | SQLite (self-hosted) | Supabase (Render) |
|---------|---------------------|-------------------|
| User creation | Admin panel in app | Supabase Dashboard only |
| Password reset | Admin panel in app | Supabase email flow |
| Setup wizard | Shown on first login | Never shown (users pre-exist) |
| Audit log | Separate `iris_audit.db` | `audit_log` table in Supabase DB |
| Full-text search | FTS5 (SQLite virtual tables) | `tsvector` + GIN index + triggers |
| Cold start | N/A | ~30–60s on first request (Render free tier spins down after inactivity) |
| Concurrency | SQLite WAL (single writer) | PostgreSQL (full concurrent writes) |
| AI thumbnail generation | Supported | Not supported (no filesystem) |

### Cold start note

Render free-tier web services spin down after 15 minutes of inactivity. The first request after a cold period may take 30–60 seconds while the Python process starts and the asyncpg pool initialises. Subsequent requests are fast. Upgrade to a paid plan to keep the service always running.

---

## Troubleshooting

**`User not found or inactive` on login**

The `profiles` row may not have been created. Check `Authentication → Users` in Supabase to confirm the user exists, then check the `profiles` table:

```sql
SELECT * FROM profiles WHERE username = 'user@example.com';
```

If missing, the trigger may have failed — manually insert:

```sql
INSERT INTO profiles (id, username, role)
SELECT id, email, 'viewer' FROM auth.users WHERE email = 'user@example.com';
```

**CORS errors on API calls**

Ensure `IRIS_CORS_ORIGINS` on the backend service matches your frontend URL exactly (e.g. `https://iris-frontend.onrender.com`). Include the protocol (`https://`) and do not include a trailing slash.

**API 502/503 errors**

The backend may be cold-starting. Wait 30–60 seconds and retry. Check Render logs for startup errors. Ensure all `SUPABASE_*` environment variables are set correctly.

**`Supabase not configured` error**

One or more `SUPABASE_*` environment variables is missing. Check all variables in the Render Dashboard for both services.

**Database connection errors**

Ensure `SUPABASE_DB_URL` uses the **Transaction pooler** URL (port 6543), not the direct connection (port 5432). The pooler is required for connection management.
