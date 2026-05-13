# ADR-172: Derive OAuth authorization_endpoint frontend URL from CORS origins

Status: Accepted (2026-05-13)
Refines: [ADR-171](ADR-171-OAuth-Authorization-Endpoint-Points-At-Frontend.md)

## Context

ADR-171 (v6.0.11) made iris-api's `authorization_endpoint` in the RFC 8414 metadata source from `IRIS_WEB_URL`. The env var was added to `render.yaml` for the iris-api service. But after deploying v6.0.11, the live metadata still advertised the API host:

```bash
$ curl https://iris-api-gtb3.onrender.com/.well-known/oauth-authorization-server
{"authorization_endpoint": "https://iris-api-gtb3.onrender.com/oauth/authorize", ...}
```

Root cause: **Render Blueprint-sync gotcha.** Env-var additions in `render.yaml` don't auto-apply to existing services — they only take effect on initial service creation or via a manual Blueprint re-sync. The same issue hit `IRIS_MCP_PUBLIC_URL` on iris-mcp in v6.0.9 testing; the user had to add it manually in the Render dashboard.

Two paths to fix per service:

1. Manually add the env var in the Render dashboard (operator action per service).
2. Make the code robust to the env var being unset.

For long-term reliability, (2) is better. Operators forget to sync env vars; "wired to the env var" is one more thing that can drift.

## Decision

When `IRIS_WEB_URL` is unset, derive the frontend URL from `IRIS_CORS_ORIGINS`. The first non-localhost entry (skipping `http://localhost:*` and `http://127.0.0.1:*`) is the frontend host. This works because:

- iris-api requires CORS origins to be configured for the frontend to call it (browser-side `fetch`).
- `IRIS_CORS_ORIGINS` has been set since v6.0.0 (or earlier) and is guaranteed to be present on any deployed iris-api.
- The first non-localhost entry is the public frontend URL by construction.

Resolution order in `_authorization_endpoint`:

1. `IRIS_WEB_URL` env var — explicit, operator-controlled.
2. First non-localhost entry in `IRIS_CORS_ORIGINS` — auto-derived fallback.
3. `api_base` (the issuer URL) — last-resort fallback for dev environments running iris-api alone.

## Why not just always use CORS_ORIGINS

`IRIS_WEB_URL` stays as the primary because:

- Explicit > implicit. An operator who wants to override the frontend URL (e.g. for a multi-domain deployment with a separate OAuth-only frontend) should be able to set the env var.
- Backwards compatibility with v6.0.11.
- Documenting the relationship as "we use the frontend URL, fall back to CORS_ORIGINS first non-localhost, fall back to the issuer" is clearer than just "we use CORS_ORIGINS".

## Why skip localhost

`IRIS_CORS_ORIGINS` in development typically contains both `http://localhost:5173` (dev frontend) and the production frontend URL. The localhost entries shouldn't be picked when deciding the OAuth `authorization_endpoint`, because:

- The metadata is served to remote MCP clients (claude.ai etc.), which can't reach `localhost`.
- If localhost slips into the metadata, every OAuth flow from external clients breaks.

Skipping `localhost` and `127.0.0.1` covers the standard dev origins. Other dev-only hostnames (e.g. `dev.local`) would need explicit `IRIS_WEB_URL` to override — acceptable edge case.

## Consequences

- One new helper (`_frontend_from_cors_origins`) in `app.oauth.router`.
- `_authorization_endpoint` resolution order extended from 2 levels to 3.
- 4 new regression tests:
  - Uses first non-localhost CORS origin when `IRIS_WEB_URL` is unset.
  - `IRIS_WEB_URL` wins over the CORS-origin fallback.
  - Skips `localhost` and `127.0.0.1` entries.
  - Strips trailing slashes.
- One existing test (`test_authorization_endpoint_falls_back_to_api_when_unset`) updated: the test now needs to clear both `IRIS_WEB_URL` AND set `IRIS_CORS_ORIGINS` to localhost-only to exercise the API-host fallback path.
- Version bump v6.0.11 → v6.0.12. Patch-level (config robustness, no API surface change).

## Verification

- 40/40 backend OAuth tests pass.
- Post-deploy: `curl https://iris-api-gtb3.onrender.com/.well-known/oauth-authorization-server` reports `authorization_endpoint: https://iris-uat.chrisbarlow.nz/oauth/authorize` regardless of whether `IRIS_WEB_URL` is set on the service — auto-derived from the existing `IRIS_CORS_ORIGINS`.

## See also

- [ADR-171](ADR-171-OAuth-Authorization-Endpoint-Points-At-Frontend.md) — the v6.0.11 fix this refines.
- Issue [#119](https://github.com/cgbarlow/iris/issues/119) — nine-revision fix history.
