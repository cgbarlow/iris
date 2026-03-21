# ADR-096: Replace Netlify with Render for Supabase Cloud Deployment

**Status:** Accepted
**Date:** 2026-03-21
**Supersedes:** ADR-094 (hosting decision only — Supabase database/auth retained)
**Depends on:** ADR-094 (Supabase deployment mode), ADR-095 (Row Level Security)

## Context

ADR-094 specified Netlify as the hosting platform for the optional Supabase cloud deployment. During
the first deployment we discovered that **Netlify Functions only support JavaScript, TypeScript, and
Go** — Python is not a supported runtime. The FastAPI backend (served via Mangum/Lambda) could not
deploy on Netlify.

The frontend deployed successfully as a static SvelteKit SPA, but all `/api/*` requests returned 404
because the Python function was never created by the Netlify build system.

### Options considered

| Option | Pros | Cons |
|--------|------|------|
| **Rewrite backend in JS/TS** | Stays on Netlify | Massive effort, loses Python ecosystem |
| **Separate backend host + Netlify frontend** | Keeps Netlify CDN | Two platforms to manage, CORS complexity |
| **Render (static site + web service)** | Native Python, free tier, single platform | Less CDN edge caching than Netlify |
| **Railway / Fly.io** | Good Python support | Less mature static site hosting |

## Decision

Replace Netlify with **Render** for both frontend and backend hosting. Supabase remains the
database and authentication provider — no changes to migrations, RLS, auth logic, or the
`DatabasePort` abstraction.

### Architecture

```
Browser
  ↓  HTTPS
Render Static Site (frontend/build — SvelteKit SPA)
  ↓  VITE_API_BASE_URL (cross-origin fetch)
Render Web Service (backend — FastAPI via uvicorn)
  ↓  asyncpg (statement_cache_size=0)
Supabase PostgreSQL (Transaction Pooler, port 6543)
```

Two Render services defined in `render.yaml` (Infrastructure as Code Blueprint):

1. **iris-frontend** — Static Site serving the SvelteKit SPA build with `/* → /index.html` rewrite
   for client-side routing.
2. **iris-api** — Python Web Service running FastAPI via uvicorn. Installed with
   `pip install -e ".[supabase]"` to include `asyncpg`.

### Key changes

- **`VITE_API_BASE_URL`** — new environment variable. Frontend and backend are separate origins on
  Render, so API calls need an absolute URL prefix (e.g. `https://iris-api.onrender.com`). Defaults
  to empty string for backward compatibility in self-hosted SQLite mode.
- **CORS** — already configurable via `IRIS_CORS_ORIGINS` env var; set to the Render frontend URL.
- **`mangum` removed** — no longer needed (uvicorn serves directly, not Lambda).
- **`render.yaml`** replaces `netlify.toml` as the deployment manifest.

## Consequences

- Netlify artifacts deleted: `netlify.toml`, `netlify/functions/`, deployment guide.
- Frontend `apiFetch()` and login page prefix all API paths with `VITE_API_BASE_URL`.
- `adapter-static` used for all cloud builds (RENDER env var or VITE_DB_BACKEND=supabase).
- Deployment guide rewritten for Render.
- No changes to Supabase configuration, migrations, RLS, or auth flow.
