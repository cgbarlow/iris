# SPEC-171-A: Point AS `authorization_endpoint` at the frontend, not the API

ADR: [ADR-171](../ADR-171-OAuth-Authorization-Endpoint-Points-At-Frontend.md)

## Summary

iris-api's RFC 8414 metadata at `/.well-known/oauth-authorization-server` advertised `authorization_endpoint: https://iris-api-gtb3.onrender.com/oauth/authorize`. iris-api has no GET handler at `/oauth/authorize` — the user-facing consent screen is a SvelteKit page on the **frontend** at `https://iris-uat.chrisbarlow.nz/oauth/authorize`. Sign-in attempts landed on a hard `{"detail":"Not Found"}` 404.

Fix: source `authorization_endpoint` from `IRIS_WEB_URL`. Token / registration / revocation endpoints stay on the API host — those are machine-to-machine endpoints with no browser involved.

## Backend changes

### `backend/app/oauth/router.py`

Add a helper that builds the authorization_endpoint URL, reading `IRIS_WEB_URL` with fallback to the API issuer (dev-environment convenience):

```python
import os

def _authorization_endpoint(api_base: str) -> str:
    """Build the user-facing authorization-endpoint URL.

    The OAuth 2.1 authorization endpoint is a BROWSER endpoint — the
    OAuth client redirects the user's browser there, the user sees a
    login + consent screen, and the page redirects back to the
    client's redirect_uri with an authorization code.

    In Iris's split-service deployment the user-facing UI lives on the
    SvelteKit frontend (IRIS_WEB_URL), NOT on the FastAPI backend.
    """
    web_url = os.environ.get("IRIS_WEB_URL", "").rstrip("/")
    return f"{web_url or api_base}/oauth/authorize"
```

Wire it into `authorization_server_metadata`:

```python
return AuthorizationServerMetadata(
    issuer=base,
    authorization_endpoint=_authorization_endpoint(base),   # ← frontend
    token_endpoint=f"{base}/oauth/token",                    # API host
    registration_endpoint=f"{base}/oauth/register",          # API host
    revocation_endpoint=f"{base}/oauth/revoke",              # API host
    ...
)
```

### `render.yaml` for the iris-api service

Add `IRIS_WEB_URL=https://iris-uat.chrisbarlow.nz` to the iris-api `envVars` list. iris-mcp already has this set for entity-link decoration (v5.6.1). The Render Blueprint-sync gotcha applies: existing services don't auto-pick up env-var additions; the operator may need to add it manually in the dashboard for the existing iris-api service. v6.0.12 (ADR-172) addresses this with an auto-derived fallback so the manual step becomes optional.

### Frontend (no change)

The frontend's `oauth/authorize/+page.svelte` already exists and correctly handles the OAuth flow:
- Reads query params from the request URL.
- POSTs them to iris-api's `/api/oauth/authorize/prepare` (with the user's session bearer) to validate.
- Renders the consent screen with the returned `request_id`.
- On Allow, POSTs `/api/oauth/authorize/decision` and `window.location.href = result.redirect_to`.

If the user isn't signed in, the page bounces through `/login?redirect=...` first.

## Tests

### `backend/tests/test_oauth/test_metadata.py`

New `TestAuthorizationEndpointFromIrisWebUrl` class (3 cases):

1. `test_authorization_endpoint_uses_iris_web_url` — with `IRIS_WEB_URL=https://web.example.com` set, `authorization_endpoint` is `https://web.example.com/oauth/authorize`. Token/register/revoke endpoints stay on the API issuer.
2. `test_authorization_endpoint_strips_trailing_slash` — `IRIS_WEB_URL=https://web.example.com/` (with slash) produces a clean `https://web.example.com/oauth/authorize` (no double-slash).
3. `test_authorization_endpoint_falls_back_to_api_when_unset` — without `IRIS_WEB_URL`, falls back to the API issuer. Metadata is well-formed (404 if clicked, but won't break tests / dev environments).

## Versioning

`mcp/pyproject.toml`: 6.0.10 → 6.0.11. `frontend/package.json` matched. (Backend `pyproject.toml` version stays at 1.2.0 — historically unchanged across the v6.0.x line.)

## Acceptance criteria

- [ ] `curl https://iris-api-gtb3.onrender.com/.well-known/oauth-authorization-server` reports `authorization_endpoint: https://iris-uat.chrisbarlow.nz/oauth/authorize`.
- [ ] Token / registration / revocation endpoints in the same payload stay on `iris-api-gtb3.onrender.com`.
- [ ] claude.ai → tap Sign in on Iris connector → browser opens the SvelteKit consent page (not a 404). Sign in if needed → consent screen → tap Allow → redirected back to claude.ai with auth code.
- [ ] 39/39 backend OAuth tests pass (36 existing + 3 new).
