# ADR-171: AS `authorization_endpoint` must point at the frontend, not the API

Status: Accepted (2026-05-13)
Extends: [ADR-164](ADR-164-OAuth-2.1-for-MCP.md), [ADR-170](ADR-170-Require-Bearer-On-MCP-HTTP-Endpoint.md)

## Context

ADR-170 (v6.0.10) added the missing spec-required 401 + WWW-Authenticate trigger so claude.ai's MCP client now correctly initiates the OAuth flow. Live testing immediately surfaced the next break: when the user tapped "Sign in" on the Iris connector in claude.ai mobile, the browser redirected to the Authorization Server's `authorization_endpoint` and landed on a hard `{"detail":"Not Found"}` 404.

Root cause: the RFC 8414 AS metadata published at `/.well-known/oauth-authorization-server` advertises:

```json
{
  "authorization_endpoint": "https://iris-api-gtb3.onrender.com/oauth/authorize",
  ...
}
```

But the iris-api FastAPI app has **no** GET handler for `/oauth/authorize`. The authorization endpoint is a *browser* endpoint — the OAuth client redirects the user's browser there, the user sees a login + consent screen, the page redirects back to the client's `redirect_uri` with an authorization code. In Iris's split-service deployment that screen lives on the **SvelteKit frontend** at `frontend/src/routes/oauth/authorize/+page.svelte`, served at `https://iris-uat.chrisbarlow.nz/oauth/authorize`. The frontend page reads the query params, POSTs them to the API's `/api/oauth/authorize/prepare` to validate, renders the consent UI, and on Allow POSTs `/api/oauth/authorize/decision` for the redirect-with-code.

The backend has only the JSON helpers (`prepare`, `decision`, `token`, `register`, `revoke`) — no user-facing GET at `/oauth/authorize`. v6.0.0 → v6.0.10 advertised the wrong host for the user-facing endpoint, so every OAuth attempt 404'd as soon as it redirected.

## Decision

In `backend/app/oauth/router.py:authorization_server_metadata`, source the `authorization_endpoint` URL from the `IRIS_WEB_URL` environment variable (the frontend host) and fall back to the API issuer URL only when the env var is unset (dev convenience):

```python
def _authorization_endpoint(api_base: str) -> str:
    web_url = os.environ.get("IRIS_WEB_URL", "").rstrip("/")
    return f"{web_url or api_base}/oauth/authorize"
```

The token / registration / revocation endpoints stay on the API host — those are machine-to-machine endpoints (no browser involved).

Add `IRIS_WEB_URL = https://iris-uat.chrisbarlow.nz` to the iris-api service's env vars in `render.yaml`. (iris-mcp already had it for entity-link decoration since v5.6.1.)

## Why not redirect on the API side

Considered: catch GET `/oauth/authorize` on the API host and redirect to the frontend. Rejected:

- AS metadata still needs to be correct for spec compliance — clients SHOULD treat the metadata's `authorization_endpoint` as canonical and ignore servers that redirect away from it.
- A redirect adds a hop (latency, more failure modes) on every sign-in.
- The fix at the metadata level is one line.

## Why not move the page to the API

The consent UI is user-facing UI, with the same look/feel as the rest of iris-uat: shared layout, theming, login redirect, DOMPurify sanitisation of DCR-supplied `client_name`. Hoisting it into the FastAPI codebase would duplicate all that. The SPA boundary is the right place for the UI.

## Why `IRIS_WEB_URL` (the same env var already used elsewhere)

- iris-mcp already reads `IRIS_WEB_URL` for entity-link decoration (`web_url` fields on tool responses, since v5.6.1).
- One env var = one source of truth for "where the frontend lives".
- The fallback (`api_base`) gives developers a meaningful response when running iris-api alone without a frontend — the metadata is well-formed even though the URL won't actually serve a consent page.

## Consequences

- One backend code change (`_authorization_endpoint` helper) and one `os` import.
- One `render.yaml` env var addition for the iris-api service.
- Three new regression tests pin: `authorization_endpoint` uses `IRIS_WEB_URL`; trailing slashes are stripped; fallback to issuer when unset. The other endpoints (token/register/revoke) keep using the API host — pinned by the test.
- Version bump v6.0.10 → v6.0.11. Patch-level (config fix, no API surface change).

## Verification

- All `backend/tests/test_oauth/` cases pass (36/36).
- Post-deploy: `curl https://iris-api-gtb3.onrender.com/.well-known/oauth-authorization-server` shows `"authorization_endpoint": "https://iris-uat.chrisbarlow.nz/oauth/authorize"`.
- claude.ai → tap Sign in on Iris connector → browser opens to the frontend page → consent screen renders → user clicks Allow → redirected back to claude.ai with auth code → bearer issued → write tools work.

## See also

- [ADR-164](ADR-164-OAuth-2.1-for-MCP.md) — original OAuth 2.1 design.
- [ADR-169](ADR-169-OAuth-Metadata-URL-Fix.md) — fixed Protected Resource metadata URLs (AS-side counterpart).
- [ADR-170](ADR-170-Require-Bearer-On-MCP-HTTP-Endpoint.md) — added the 401 trigger that surfaced this bug.
- RFC 8414 §2 — AS metadata `authorization_endpoint` definition.
- Issue [#119](https://github.com/cgbarlow/iris/issues/119) — eight-revision fix history culminating here.
