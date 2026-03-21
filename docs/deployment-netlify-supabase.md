# Deploying Iris to Netlify + Supabase

This guide covers deploying Iris as a static SvelteKit frontend on **Netlify** with a **FastAPI** backend served through Netlify Functions, backed by a **Supabase** PostgreSQL database and Supabase Auth.

> **Default deployment is SQLite (self-hosted).** Netlify + Supabase is an optional cloud deployment path. See the main README for standard self-hosted setup.

## Prerequisites

- A [Netlify](https://netlify.com) account
- A [Supabase](https://supabase.com) account
- The Iris repository cloned locally (or forked on GitHub)

---

## Step 1 — Create a Supabase project

1. Log in to [app.supabase.com](https://app.supabase.com) and click **New project**.
2. Choose an organisation, project name, database password, and region. Save the database password securely.
3. After the project provisions, go to **Settings → API** and note:
   - **Project URL** (`SUPABASE_URL`)
   - **anon / public key** (`SUPABASE_ANON_KEY`)
   - **service_role / secret key** (`SUPABASE_SERVICE_ROLE_KEY`)
4. Go to **Settings → API → JWT Settings** and note:
   - **JWT Secret** (`SUPABASE_JWT_SECRET`)
5. Go to **Settings → Database** and note the **Connection string (URI)** — use the *Transaction pooler* URL for serverless functions (`SUPABASE_DB_URL`). Replace `[YOUR-PASSWORD]` with your database password.

---

## Step 2 — Run the PostgreSQL migrations

1. In your Supabase project, go to **SQL Editor** and open a new query.
2. Run each migration file in order from `backend/app/migrations/supabase/`:

   ```
   m001_roles_users.sql
   m002_elements_relationships_diagrams.sql
   m003_audit_log.sql
   m004_comments_bookmarks.sql
   m005_search.sql
   m006_settings.sql
   m007_thumbnails.sql
   m008_element_tags.sql
   m009_diagram_tags.sql
   m010_thumbnail_themes.sql
   m011_model_hierarchy.sql
   m012_sets.sql
   m013_set_thumbnails.sql
   m014_sets_partial_unique.sql
   m015_package_relationships.sql
   m016_naming_rename.sql
   m017_views.sql
   m018_package_bookmarks.sql
   m019_recycle_bin.sql
   m020_diagram_type_notation_registry.sql
   m021_edit_locks.sql
   m022_element_notation.sql
   m023_new_diagram_types.sql
   m024_themes.sql
   m025_diagram_links.sql
   m026_ai_providers.sql
   m027_profiles.sql
   ```

   Run each file in the SQL Editor, in order.

3. `m027_profiles.sql` creates the `profiles` table and a trigger that auto-creates a profile row whenever Supabase Auth creates a new user. You do **not** need to insert profile rows manually.

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

## Step 4 — Create a Netlify site

### Option A: Deploy from GitHub (recommended)

1. Push your Iris fork/repo to GitHub.
2. Log in to Netlify, click **Add new site → Import an existing project**.
3. Connect to GitHub and select your Iris repository.
4. Netlify will detect `netlify.toml` automatically. The build settings are pre-configured.

### Option B: Netlify CLI

```sh
npm install -g netlify-cli
netlify login
netlify init
```

---

## Step 5 — Set environment variables in Netlify

In your Netlify site, go to **Site settings → Environment variables** and add:

| Variable | Value | Description |
|----------|-------|-------------|
| `IRIS_DB_BACKEND` | `supabase` | Enables Supabase deployment mode |
| `SUPABASE_URL` | `https://xxxx.supabase.co` | From Supabase Settings → API |
| `SUPABASE_ANON_KEY` | `eyJ...` | Supabase anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | `eyJ...` | Supabase service_role key |
| `SUPABASE_DB_URL` | `postgresql://...` | Transaction pooler connection string |
| `SUPABASE_JWT_SECRET` | `your-jwt-secret` | From Supabase Settings → API → JWT Settings |
| `VITE_DB_BACKEND` | `supabase` | Frontend deployment mode flag |
| `VITE_SUPABASE_URL` | `https://xxxx.supabase.co` | Frontend Supabase URL |
| `VITE_SUPABASE_ANON_KEY` | `eyJ...` | Frontend Supabase anon key |

> **Security note:** `VITE_*` variables are embedded in the frontend bundle at build time and visible to users. Use the **anon** key (not service_role) for `VITE_SUPABASE_ANON_KEY`. The `SUPABASE_SERVICE_ROLE_KEY` is only available to the Netlify Function (backend).

---

## Step 6 — Deploy

1. Trigger a deploy from Netlify (or push to your linked GitHub branch).
2. Netlify runs: `cd frontend && npm ci && npm run build`
3. The SvelteKit frontend is published to `frontend/build`.
4. The FastAPI backend is served from `netlify/functions/api.py` via Mangum.

### Verify the deployment

- Visit your Netlify URL — you should see the Iris login page.
- Log in with the admin credentials created in Step 3.
- API calls are routed through `/.netlify/functions/api` by the redirect rule in `netlify.toml`.

---

## Architecture overview

```
Browser
  ↓  HTTPS
Netlify CDN (frontend/build — SvelteKit static)
  ↓  /api/* redirect
Netlify Function (netlify/functions/api.py — FastAPI via Mangum)
  ↓  asyncpg
Supabase PostgreSQL (Transaction Pooler)

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

## Limitations and differences from SQLite mode

| Feature | SQLite (self-hosted) | Supabase (Netlify) |
|---------|---------------------|-------------------|
| User creation | Admin panel in app | Supabase Dashboard only |
| Password reset | Admin panel in app | Supabase email flow |
| Setup wizard | Shown on first login | Never shown (users pre-exist) |
| Audit log | Separate `iris_audit.db` | `audit_log` table in Supabase DB |
| Full-text search | FTS5 (SQLite virtual tables) | `tsvector` + GIN index + triggers |
| Cold start | N/A | ~1–3s on first request (Netlify Function) |
| Concurrency | SQLite WAL (single writer) | PostgreSQL (full concurrent writes) |
| AI thumbnail generation | Supported | Not supported (no filesystem) |

### Cold start note

Netlify Functions are serverless and spin down after inactivity. The first request after a cold period may take 1–3 seconds while the FastAPI + asyncpg pool initialises. Subsequent requests are fast.

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

**API 404 on `/api/*` routes**

Confirm `netlify.toml` is at the repository root and the `[[redirects]]` block is present. Check the Netlify deploy logs for function build errors.

**`Supabase not configured` error**

One or more `SUPABASE_*` environment variables is missing. Check all variables in **Site settings → Environment variables**.

**Database connection errors in function logs**

Ensure `SUPABASE_DB_URL` uses the **Transaction pooler** URL (port 6543), not the direct connection (port 5432). Serverless functions must use the pooler to avoid connection exhaustion.
