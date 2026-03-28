# SPEC-110-A: Scenia Render Service

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-110-A |
| **ADR** | [ADR-110](../ADR-110-Scenia-Render-Service.md) |
| **Status** | Draft |
| **Date** | 2026-03-27 |

## Overview

Add Scenia as a third Render Blueprint service, building from the external fork `cgbarlow/waylonkenning_scenia` (branch `feature/iris-embed`) as a static site.

## render.yaml Service Definition

```yaml
  - type: web
    name: scenia
    runtime: static
    repo: https://github.com/cgbarlow/waylonkenning_scenia
    branch: feature/iris-embed
    buildCommand: npm ci && npm run build
    staticPublishPath: dist
    envVars:
      - key: VITE_API_BASE_URL
        sync: false
    routes:
      - type: rewrite
        source: /*
        destination: /index.html
```

Additionally, `VITE_SCENIA_URL` (sync: false) is added to the `iris-frontend` service.

## Environment Variable Matrix

| Service | Variable | Value | Type |
|---------|----------|-------|------|
| iris-frontend | `VITE_SCENIA_URL` | `https://scenia.onrender.com` | Manual (sync: false) |
| scenia | `VITE_API_BASE_URL` | `https://iris-api.onrender.com` | Manual (sync: false) |
| iris-api | `IRIS_CORS_ORIGINS` | `https://iris-frontend.onrender.com,https://scenia.onrender.com` | Manual (sync: false) |

## Authentication Flow

1. User clicks "View in Scenia" in the Iris frontend.
2. `openScenia()` (`frontend/src/lib/scenia/config.ts`) reads the JWT from sessionStorage and constructs a URL: `SCENIA_URL?apiUrl=IRIS_API_URL&token=JWT&setId=SET_ID`.
3. Scenia opens in a new browser tab, reads the query parameters, and uses the JWT in `Authorization: Bearer` headers when calling `/api/scenia/data` on the Iris backend.
4. No separate authentication system is needed — Scenia reuses the Iris JWT.

## CORS

The Iris backend reads `IRIS_CORS_ORIGINS` as a comma-separated list (`backend/app/config.py:77-80`). The Scenia Render URL must be included so cross-origin fetch requests from the Scenia SPA to `/api/scenia/data` succeed.

## Build Pipeline

- Scenia fork builds with Vite (`npm ci && npm run build`), outputting to `dist/`.
- Render auto-deploys on push to the `feature/iris-embed` branch of the fork.
- The Iris frontend and Scenia have independent build cycles — changes to one do not trigger a rebuild of the other.

## Acceptance Criteria

1. `render.yaml` contains three services: `iris-frontend`, `scenia`, `iris-api`.
2. The `scenia` service references `repo: https://github.com/cgbarlow/waylonkenning_scenia` with `branch: feature/iris-embed`.
3. `VITE_SCENIA_URL` is declared in the iris-frontend env vars.
4. Deployment guide documents the Scenia service, its env vars, and CORS requirements.
5. After deployment, clicking "View in Scenia" in the Iris frontend opens the deployed Scenia app in a new tab with working API connectivity.
