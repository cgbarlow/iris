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

All migration files are in `backend/app/migrations/supabase/` (m001–m043). They are idempotent and safe to re-run.

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

- **m001–m026**: Core schema (tables, indexes, FTS triggers for elements/diagrams, seed data)
- **m027**: `profiles` table + trigger that auto-creates a profile row when Supabase Auth creates a user (no manual inserts needed)
- **m028**: DoView notation, diagram types, mappings, and theme (seed data)
- **m029**: `ai_creation_prompts` table + 4 seeded layered prompts
- **m030**: Row Level Security on core tables (see [Verifying Row Level Security](#verifying-row-level-security))
- **m031–m034**: Schema patches (`ai_conversations` mode/thread_id, sequence order, collections table, extensions registry)
- **m035**: Scenia tables (strategies / programmes / initiatives / …) — optional, used only when the Scenia extension is enabled
- **m036–m037**: Scenia timestamp columns + `ai_conversations.set_id` nullable
- **m038**: Collections RLS policies
- **m039**: `graph_settings` table (admin defaults for knowledge-graph physics)
- **m040**: Search parity with SQLite — `search_vector` + GIN + triggers for packages/sets/collections, chain-triggers fixing INSERT-ordering on elements/diagrams (ADR-125)
- **m041**: Expanded AI creation prompts (ADR-132)
- **m042**: Personal Access Tokens (ADR-127)
- **m043**: DocRef legislation tables — required for the Iris AI Legislation feature on Supabase deployments (ADR-135, issue #24)

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

Each Render service has its own **Environment → Environment Variables** tab. All values below are `sync: false` in `render.yaml` — they are secrets per-deployment and must be entered manually (or pasted from a password manager).

### Frontend (iris-frontend)

| Variable | Example value | Description |
|----------|---------------|-------------|
| `PUBLIC_SITE_URL` | `https://<your-frontend-domain>` | Absolute base URL of this deployment. Interpolated into `src/app.html` at build time as `%sveltekit.env.PUBLIC_SITE_URL%` so Open Graph / Twitter Card `og:image` / `og:url` resolve to absolute URLs that LinkedIn / Slack / Teams / WhatsApp scrape correctly (ADR-126). Must match the custom domain or Render URL exactly; no trailing slash. |
| `VITE_API_BASE_URL` | `https://<your-api-service>.onrender.com` | URL of the **iris-api** web service (use its Render-assigned `*.onrender.com` URL or your custom domain for the API). `apiFetch` prefixes every request with this. |
| `VITE_DB_BACKEND` | `supabase` | Enables Supabase deployment mode. The frontend imports `@supabase/supabase-js` and the Supabase login flow only when this is `supabase`. |
| `VITE_SCENIA_URL` | `https://<your-scenia-service>.onrender.com` | URL of the **scenia** static site (custom domain or `*.onrender.com`). Used by `openScenia()` to open the roadmapping app in a new tab with the JWT + API URL as query params. |
| `VITE_SUPABASE_ANON_KEY` | `sb_publishable_...` | Supabase **publishable** key. Embedded in the frontend bundle at build time — safe because RLS (m030) denies direct table access to this key. |
| `VITE_SUPABASE_URL` | `https://<project-id>.supabase.co` | Supabase project URL. Used by the Supabase JS SDK for the login flow. |

> **Security note:** `VITE_*` and `PUBLIC_*` variables are embedded in the built HTML and JS bundles and visible to anyone loading the page. Use the **publishable** key (not the secret key) for `VITE_SUPABASE_ANON_KEY`. The service-role secret key belongs on the backend only.

### Scenia (scenia)

| Variable | Example value | Description |
|----------|---------------|-------------|
| `VITE_API_BASE_URL` | `https://<your-api-service>.onrender.com` | URL of the iris-api web service — same value as on the frontend service. |

> Scenia receives auth tokens at runtime via URL query parameters from the Iris frontend (see `openScenia()` in `frontend/src/lib/scenia/config.ts`). No Supabase keys are needed at build time.

### Backend (iris-api)

| Variable | Example value | Description |
|----------|---------------|-------------|
| `IRIS_CORS_ORIGINS` | `https://<your-frontend-domain>,https://<your-scenia-domain>` | Comma-separated list of allowed CORS origins — your frontend URL plus the Scenia URL. Both Iris and Scenia make cross-origin calls to this API. Include `https://`; do not include trailing slashes. |
| `IRIS_DB_BACKEND` | `supabase` | Enables Supabase deployment mode. Without this, the backend opens a local SQLite file. |
| `IRIS_DEBUG` | `false` | `true` switches the FastAPI app into debug mode (richer error pages, reloader in dev). Leave as `false` on production deployments. |
| `SUPABASE_ANON_KEY` | `sb_publishable_...` | Supabase publishable key. Same value as `VITE_SUPABASE_ANON_KEY` on the frontend. |
| `SUPABASE_DB_URL` | `postgresql://postgres:PASSWORD@aws-0-xx-xx-x.pooler.supabase.com:6543/postgres?sslmode=require` | Transaction pooler connection string (port **6543**, not 5432). Runtime app connections only — migrations use the direct-connection URL on port 5432 (see Step 2). |
| `SUPABASE_JWT_SECRET` | `your-jwt-secret` | JWT secret from Supabase **Settings → API Keys → JWT Settings**. The backend uses this to verify tokens issued by Supabase Auth. |
| `SUPABASE_SERVICE_ROLE_KEY` | `sb_secret_...` | Supabase **secret** key — backend only. Grants RLS-bypassing access. **Never** expose this in the frontend bundle. |
| `SUPABASE_URL` | `https://<project-id>.supabase.co` | Supabase project URL. Same value as `VITE_SUPABASE_URL`. |

### Optional backend rate-limit overrides

Default rate limits are defined in `backend/app/config.py`. Override only if you need to deviate from the defaults — otherwise leave these unset on Render.

| Variable | Default | Description |
|----------|---------|-------------|
| `IRIS_RATE_LIMIT_LOGIN` | `10` | Failed-login attempts allowed per IP per 60-second sliding window. |
| `IRIS_RATE_LIMIT_REFRESH` | `30` | Token refresh requests per IP per 60 seconds. |
| `IRIS_RATE_LIMIT_GENERAL` | `1000` | All other API calls per IP per 60 seconds. |
| `IRIS_RATE_LIMIT_ANON_AI` | `10` | Anonymous Ask AI requests per IP per **60-minute** window (ADR-123). Separate bucket from `GENERAL` so unauthenticated AI usage is bounded without throttling signed-in users. |

### Custom domains (optional)

If you want branded hostnames for the frontend and Scenia rather than the Render-assigned `*.onrender.com` URLs:

1. In each Render service → **Settings → Custom Domains**, add your hostname and follow the CNAME / ALIAS instructions.
2. Update the env vars above to reference your custom domain instead of the `*.onrender.com` default (the frontend's `VITE_API_BASE_URL`, `VITE_SCENIA_URL`, `PUBLIC_SITE_URL`, and the backend's `IRIS_CORS_ORIGINS`).
3. Redeploy each service so the new values bake into the build.

> The `iris-api` service can usually keep its `*.onrender.com` URL — there's little upside to exposing the backend under a custom domain, and CORS handling stays simpler with a stable Render URL.

---

## Step 6 — Verify the deployment

1. **Anonymous read-only load.** Visit your frontend URL in an incognito window. The Iris dashboard should render immediately (no login redirect) — ADR-123 / SPEC-123-A behaviour. The sidebar should show: Iris AI, Dashboard, Collections, Sets, Diagrams, Elements, Settings. The header should show **User Guide** and **Sign in** links.
2. **Sign in.** Click **Sign in**, enter the admin credentials from Step 3. Sidebar should now include Bookmarks / Import / Recycle Bin and the Admin submenu.
3. **CRUD smoke.** Create a collection, add a set, add a package, add a diagram, edit the diagram canvas — verify write operations work.
4. **Search.** Type a term that should match something you just created — confirm non-empty results (ADR-121 + ADR-125 behaviour).
5. **Ask AI.** Open `/ask`, pick the default provider, send a test question — confirm streaming response.
6. **Social preview.** Paste the frontend URL into Slack or a [Facebook Sharing Debugger](https://developers.facebook.com/tools/debug/) — confirm the preview card renders with the dashboard screenshot (ADR-126). If the image doesn't show, `PUBLIC_SITE_URL` is probably missing from the frontend service.

### Verify CORS

If API calls fail with CORS errors (browser console: "Access-Control-Allow-Origin missing"), check that `IRIS_CORS_ORIGINS` on the backend service lists **every** frontend origin exactly — `https://`, no trailing slash, comma-separated if multiple. The most common miss is forgetting to include the Scenia URL when the Scenia extension is enabled.

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

One or more `SUPABASE_*` environment variables is missing. Check all variables in the Render Dashboard for the **iris-api** service against the full list in Step 5 — the backend needs all seven Supabase-related vars plus `IRIS_DB_BACKEND=supabase`.

**Database connection errors**

Ensure `SUPABASE_DB_URL` uses the **Transaction pooler** URL (port 6543), not the direct connection (port 5432). The pooler is required for connection management. Migrations in Step 2 use the direct-connection URL (port 5432) — don't mix them up.

**Social preview card doesn't show an image**

`PUBLIC_SITE_URL` is missing or wrong on the **iris-frontend** service. The variable is interpolated at build time, so after setting it you must trigger a rebuild (Render → Manual Deploy, or push any commit). Use the [Facebook Sharing Debugger](https://developers.facebook.com/tools/debug/) to re-scrape the URL once fixed; Slack / Teams cache aggressively and may need a new unique URL (e.g. `?v=2`) to refresh.

**Search returns nothing**

Check that `m040_search_all_entities.sql` has been applied — run the verification query from [Verifying Row Level Security](#verifying-row-level-security) but adapted:

```sql
SELECT tablename, column_name FROM information_schema.columns
WHERE table_schema = 'public' AND column_name = 'search_vector'
ORDER BY tablename;
```

You should see `search_vector` columns on `collections`, `diagrams`, `elements`, `packages`, and `sets`. If any are missing, re-run the migration (ADR-125).

**Anonymous Ask AI is rejecting every request**

`IRIS_RATE_LIMIT_ANON_AI` defaults to 10 requests per IP per hour. If a test harness is hammering the endpoint behind a shared NAT, bump the value on the **iris-api** service. Rate limits are per Render instance memory — restarting the service resets every bucket.
