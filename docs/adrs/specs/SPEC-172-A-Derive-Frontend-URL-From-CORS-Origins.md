# SPEC-172-A: Derive OAuth `authorization_endpoint` frontend URL from CORS origins

ADR: [ADR-172](../ADR-172-Derive-Frontend-URL-From-CORS-Origins.md)

## Summary

Make the AS `authorization_endpoint` derivation robust to `IRIS_WEB_URL` not being set. Fall through to the first non-localhost entry in `IRIS_CORS_ORIGINS`, which has been set since v6.0.0 and is guaranteed to contain the public frontend URL (the frontend can't call iris-api without being in the CORS allow-list). Render Blueprint sync doesn't auto-apply env-var additions to existing services — this fallback eliminates the env-var dependency for the common case.

## Backend changes

### `backend/app/oauth/router.py`

Extend `_authorization_endpoint` with a CORS-origins fallback. Resolution order:

1. `IRIS_WEB_URL` env var — explicit, operator-controlled.
2. First non-localhost entry in `IRIS_CORS_ORIGINS` — auto-derived.
3. `api_base` (the issuer URL) — last-resort dev fallback.

```python
def _authorization_endpoint(api_base: str) -> str:
    web_url = os.environ.get("IRIS_WEB_URL", "").rstrip("/")
    if not web_url:
        web_url = _frontend_from_cors_origins()
    return f"{web_url or api_base}/oauth/authorize"


def _frontend_from_cors_origins() -> str:
    """Return the first non-localhost entry in IRIS_CORS_ORIGINS,
    rstrip-ed of trailing slashes. Empty string when none found.
    Skips http://localhost:* and http://127.0.0.1:* — those are
    dev-only allow-listed origins that don't reflect the public
    frontend URL.
    """
    raw = os.environ.get("IRIS_CORS_ORIGINS", "")
    for origin in (s.strip() for s in raw.split(",")):
        if not origin:
            continue
        if origin.startswith(("http://localhost", "http://127.0.0.1")):
            continue
        return origin.rstrip("/")
    return ""
```

### Why skip localhost

`IRIS_CORS_ORIGINS` in development typically contains both `http://localhost:5173` (dev frontend) and the production frontend URL. The metadata document is served to remote MCP clients, which can't reach `localhost`. If a localhost entry leaked into `authorization_endpoint`, every OAuth flow from external clients would break.

## Tests

### `backend/tests/test_oauth/test_metadata.py`

New `TestAuthorizationEndpointFromCorsOrigins` class (4 cases):

1. `test_uses_first_non_localhost_cors_origin` — with `IRIS_WEB_URL` unset and `IRIS_CORS_ORIGINS="http://localhost:5173,https://iris-uat.chrisbarlow.nz"`, `authorization_endpoint` is `https://iris-uat.chrisbarlow.nz/oauth/authorize`.
2. `test_iris_web_url_wins_over_cors` — both env vars set with different hostnames; `IRIS_WEB_URL` wins.
3. `test_skips_localhost_127_0_0_1` — `127.0.0.1` entries are skipped just like `localhost`.
4. `test_strips_trailing_slash_from_cors_entry` — trailing-slash hygiene matches the IRIS_WEB_URL path.

Existing `test_authorization_endpoint_falls_back_to_api_when_unset` is updated to set `IRIS_CORS_ORIGINS` to localhost-only so the API fallback path actually exercises (otherwise the CORS auto-derive would catch it first).

## Versioning

`mcp/pyproject.toml`: 6.0.11 → 6.0.12. `frontend/package.json` matched.

## Acceptance criteria

- [ ] `curl https://iris-api-gtb3.onrender.com/.well-known/oauth-authorization-server` reports a frontend URL as `authorization_endpoint`, even if `IRIS_WEB_URL` is not set on iris-api in Render. (The fallback derives it from `IRIS_CORS_ORIGINS`.)
- [ ] If `IRIS_CORS_ORIGINS` contains the Render-internal URL first (`https://iris-frontend-xwzi.onrender.com,https://iris-uat.chrisbarlow.nz`), the metadata uses that — explicit `IRIS_WEB_URL` is the way to force the custom domain.
- [ ] 40/40 backend OAuth tests pass (36 existing + 4 new).
