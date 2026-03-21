# SPEC-096-A: Render Deployment

**ADR:** [ADR-096](../ADR-096-Render-Replaces-Netlify.md)
**Status:** Implemented
**Supersedes:** SPEC-094-A (hosting section only — Supabase config retained)

## Overview

Replaces Netlify with Render as the hosting platform for the optional Supabase cloud deployment.
Two Render services serve the frontend (static site) and backend (Python web service).

## Architecture

```
Render Static Site (iris-frontend)
  └── frontend/build (SvelteKit SPA, adapter-static)
  └── Rewrite: /* → /index.html

Render Web Service (iris-api)
  └── FastAPI via uvicorn
  └── pip install -e ".[supabase]" (asyncpg)
```

## Configuration

### New environment variable

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Backend URL for cross-origin API calls | `''` (relative paths) |

### Removed

| Item | Reason |
|------|--------|
| `mangum` dependency | Lambda adapter, not needed with uvicorn |
| `@sveltejs/adapter-netlify` | Replaced by `adapter-static` |
| `netlify.toml` | Netlify config |
| `netlify/functions/api.py` | Mangum Lambda wrapper |
| `netlify/functions/requirements.txt` | Lambda deps |

### render.yaml Blueprint

Defines two services:

1. **iris-frontend** (`type: web`, `runtime: static`)
   - Build: `cd frontend && npm ci && npm run build`
   - Publish: `frontend/build`
   - Rewrite: `/* → /index.html`
   - Env: `VITE_DB_BACKEND`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_BASE_URL`

2. **iris-api** (`type: web`, `runtime: python`)
   - Build: `cd backend && pip install -e ".[supabase]"`
   - Start: `uvicorn app.main:create_app --host 0.0.0.0 --port $PORT --factory`
   - Env: `IRIS_DB_BACKEND`, `SUPABASE_*`, `IRIS_CORS_ORIGINS`

Secrets use `sync: false` — entered via Render Dashboard.

## Frontend changes

### `frontend/src/lib/config.ts`

```ts
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? '';
```

### API fetch prefix

All `fetch()` calls in the frontend prefix paths with `API_BASE_URL`:

| File | Call |
|------|------|
| `src/lib/utils/api.ts` | `apiFetch()` — all API calls |
| `src/lib/utils/api.ts` | `tryRefresh()` — SQLite token refresh |
| `src/routes/login/+page.svelte` | `/api/auth/me`, `/api/auth/login`, `/api/auth/setup/*` |
| `src/routes/import/+page.svelte` | `/api/import/sparx` (FormData upload) |
| `src/routes/sets/[id]/+page.svelte` | `/api/sets/:id/thumbnail` (FormData upload) |
| `src/lib/components/SetQA.svelte` | `/api/ai/sets/:id/ask?stream=true` (SSE) |

### `frontend/svelte.config.js`

```js
const adapter = (process.env.RENDER || process.env.VITE_DB_BACKEND === 'supabase')
    ? adapterStatic({ fallback: 'index.html' })
    : adapterAuto();
```

## Backend changes

### `backend/pyproject.toml`

```toml
[project.optional-dependencies]
supabase = ["asyncpg==0.31.0"]  # mangum removed
```

### CORS

Existing `IRIS_CORS_ORIGINS` env var handles cross-origin requests. Set to the Render frontend URL.

## Backward compatibility

- `VITE_API_BASE_URL` defaults to empty string — all existing self-hosted deployments work unchanged.
- `adapter-auto` still used for local dev (no `RENDER` env var, no `VITE_DB_BACKEND=supabase`).
- No changes to Supabase migrations, RLS, auth flow, or `DatabasePort` abstraction.

## Verification

1. `cd frontend && RENDER=true npm run build` → `build/index.html` exists
2. `cd backend && pytest` → all tests pass
3. Deploy to Render, set env vars, verify login + CRUD
4. RLS: `curl` with anon key returns `[]`
