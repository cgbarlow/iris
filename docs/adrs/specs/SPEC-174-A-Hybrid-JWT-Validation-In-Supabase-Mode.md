# SPEC-174-A: Accept iris-OAuth JWTs in Supabase deployment mode

ADR: [ADR-174](../ADR-174-Hybrid-JWT-Validation-In-Supabase-Mode.md)

## Summary

In Supabase deployment mode, `_get_current_user_supabase` only validated JWTs with Supabase's signing key. iris-OAuth tokens are signed with `IRIS_JWT_SECRET` — different key, signature always fails, 401 on every bearer. Add a hybrid path: tokens with `aud="iris-mcp"` route through iris's HS256 validator using `config.auth.jwt_secret`; everything else stays on the Supabase path. Also require `IRIS_JWT_SECRET` in production (current dev default is a hardcoded string in the public repo).

## Backend changes

### `backend/app/auth/dependencies.py:_get_current_user_supabase`

Insert a branch before the existing Supabase JWT validation:

```python
async def _get_current_user_supabase(request, token):
    from app.auth.service import decode_access_token
    from app.auth.supabase_service import (
        decode_supabase_jwt, fetch_jwks, get_profile,
    )
    from jose import jwt as _jose_jwt

    config = request.app.state.config
    if config.supabase is None:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    payload: dict[str, Any] | None = None

    # 1. iris-OAuth tokens (aud="iris-mcp") → validate with iris JWT secret.
    try:
        unverified = _jose_jwt.get_unverified_claims(token)
    except JWTError:
        unverified = {}
    if unverified.get("aud") == "iris-mcp":
        try:
            payload = decode_access_token(token, config.auth)
        except JWTError as e:
            raise HTTPException(
                status_code=401,
                detail="Invalid iris-OAuth token",
            ) from e

    # 2. Everything else → existing Supabase validation.
    if payload is None:
        try:
            jwks = await fetch_jwks(config.supabase.url)
            payload = decode_supabase_jwt(
                token, config.supabase.jwt_secret, jwks,
            )
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

    # Profile lookup unchanged: same get_profile call for both paths.
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token claims")

    db = request.app.state.db_manager.main_db
    profile = await get_profile(db, str(user_id))
    if profile is None or not profile["is_active"]:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return {
        "id": profile["id"],
        "username": profile["username"],
        "role": profile["role"],
        "jti": payload.get("jti"),
    }
```

### Critical: no fall-through on signature failure

If a token claims `aud="iris-mcp"` but its signature doesn't validate against the iris JWT secret, return **401**. Do **not** try Supabase validation as a fallback. Audience is a routing claim, signature is the security boundary — letting a Supabase-signed token forge an iris-OAuth identity by adding `aud="iris-mcp"` to its (signed) payload is the failure mode this guards against (an attacker can't actually re-sign the payload, but the principle keeps the trust domains separate).

### `render.yaml` for the iris-api service

Add `IRIS_JWT_SECRET` with `sync: false` so the operator generates a per-deployment secret and pastes it into the Render dashboard. **Operator must add it manually** to existing services (Render Blueprint-sync limitation).

The fallback dev string in `config.py` keeps local development working without an env var; the comment in `render.yaml` explains the production requirement.

## Tests

### `backend/tests/test_auth/test_supabase_mode_oauth_token.py` (new)

3 cases using mock for `get_profile`:

1. `test_iris_oauth_token_validates_via_iris_secret` — iris-OAuth-shaped token signed with `config.auth.jwt_secret` → routes through iris validator → returns the user dict.
2. `test_iris_oauth_token_with_wrong_signature_401` — same `aud="iris-mcp"` but signed with the wrong secret → 401 (no fall-through to Supabase decoder).
3. `test_supabase_token_still_validates_via_supabase_path` — Supabase-shaped token (no `aud="iris-mcp"`, signed with `config.supabase.jwt_secret`) → routes through Supabase decoder → returns the user dict.

The tests construct an `AppConfig` with separate iris + Supabase JWT secrets so the routing is testable without a real Supabase JWKS endpoint.

## Versioning

`mcp/pyproject.toml`: 6.0.13 → 6.0.14. `frontend/package.json` matched.

## Operator action required after deploy

1. **Set `IRIS_JWT_SECRET` on iris-api** in the Render dashboard. Generate locally: `openssl rand -hex 32`. Paste the value into Environment → Add Environment Variable. Save → iris-api restarts. **Do not generate the secret on the agent's side** (per the secret-handling memory note — the secret would leak through chat output / tool capture).
2. **Disconnect + reconnect Iris connector in claude.ai.** Bearers signed with the previous dev-default secret won't validate against the new one. A fresh OAuth flow mints fresh bearers.

## Acceptance criteria

- [ ] `IRIS_JWT_SECRET` is set as an env var on the iris-api Render service (verifiable via `curl /v1/services/.../env-vars` → key present, value hidden as expected).
- [ ] claude.ai → Sign in → Allow → connector goes to "Connected" → `create_collection` returns 200 with the new id.
- [ ] Render API logs show 200s on `/api/sets`, `/api/collections`, etc. — no 401s after the bearer is issued.
- [ ] 120/120 OAuth + auth tests pass (117 existing + 3 new).
- [ ] An attacker can't forge a bearer using the public-repo dev default — `IRIS_JWT_SECRET` is operator-set and unique per deployment.
