# ADR-174: Accept iris-OAuth JWTs in Supabase deployment mode

Status: Accepted (2026-05-13)
Extends: [ADR-164](ADR-164-OAuth-2.1-for-MCP.md), [ADR-173](ADR-173-OAuth-Boolean-Column-Parameterisation.md)

## Context

v6.0.13 fixed the Postgres bool-vs-int crash in `create_refresh_token` and the user successfully exchanged an authorization code for an access token (`POST /oauth/token` → HTTP 200 with bearer). The connector showed as connected. But the very next write call from claude.ai surfaced:

> Iris is asking you to sign in before it'll let me create anything.

Live iris-api logs confirmed the bearer was being rejected with HTTP 401 on every authenticated route the connector tried:

```
20:13:18  POST /oauth/token            200 OK    ← token issued
20:13:27  GET  /api/prompts/scope-index 401 ✗   ← bearer rejected
20:14:51  POST /api/sets                401 ✗
```

Root cause: in Supabase deployment mode, `_get_current_user_supabase` validates the JWT using **Supabase's** signing key (ES256 via JWKS, or HS256 with `SUPABASE_JWT_SECRET`). But iris-OAuth tokens are signed with **iris's** JWT secret via `app.oauth.service.issue_access_token`:

```python
return jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)
#                          └── from IRIS_JWT_SECRET, NOT SUPABASE_JWT_SECRET
```

The two signing keys are different. The signature validation in `decode_supabase_jwt` always fails → 401. This regressed silently from v6.0.0 (when OAuth shipped) because the deployment ran SQLite mode in testing — only `_get_current_user_sqlite` validates with the iris JWT secret, so the bug only surfaces on Postgres-backed (Supabase) deployments. The end-to-end OAuth tests pass on SQLite and the bug stayed hidden.

A second, related issue surfaced in the same diagnostic: **`IRIS_JWT_SECRET` is not set in production** (no env var on the iris-api Render service). The code falls back to the dev default literal in `config.py` — which is a string in the public repo (`"dev-secret-change-in-production-must-be-at-least-32-bytes-long"`). Anyone reading the repo can forge OAuth-issued JWTs against the live deployment until this is fixed.

## Decision

Two changes:

### 1. Hybrid JWT validation in Supabase mode

`_get_current_user_supabase` now accepts two JWT issuers on the same `Authorization: Bearer` header:

- **iris-OAuth tokens** — identified by `aud="iris-mcp"` (the canonical OAuth audience set by `issue_access_token`). Signature validated with `config.auth.jwt_secret` via the existing `decode_access_token` helper. Pure iris HS256.
- **Supabase-issued tokens** — everything else. Routed through the existing `decode_supabase_jwt` path (ES256 via JWKS, HS256 fallback with `SUPABASE_JWT_SECRET`). Standard Supabase login bearer.

The branch happens at the *audience-claim* level, NOT at the signature-validation level — both paths still validate the signature against their own key. We don't fall through from one validator to the other on signature failure, so a token claiming `aud="iris-mcp"` with the wrong signature stays 401'd (would otherwise let any Supabase-signed token forge an iris-OAuth identity).

Profile lookup is unchanged: both paths use the same `get_profile(db, user_id)` because the `sub` claim is the Supabase auth.users UUID in either case (the OAuth consent screen captures `current_user["id"]`, which came from this same function pre-OAuth, so the `sub` in the issued OAuth token IS the profile id).

### 2. Add `IRIS_JWT_SECRET` to `render.yaml`

Add the env var with `sync: false` so the operator generates a per-deployment secret (`openssl rand -hex 32`) and pastes it into the Render dashboard. The fallback dev string stays in `config.py` so local development keeps working; the comment explains the production requirement.

This doesn't auto-apply to the running iris-api (Render Blueprint sync limitation — same gotcha as `IRIS_MCP_PUBLIC_URL` in v6.0.9 and `IRIS_WEB_URL` in v6.0.11). The operator must add it manually in the dashboard for an existing service.

## Why hybrid validation, not "OAuth tokens use SUPABASE_JWT_SECRET"

Considered: have `issue_access_token` sign with `SUPABASE_JWT_SECRET` in Supabase mode. Then `_get_current_user_supabase` already validates them.

Rejected because:

- It couples our OAuth token issuance to Supabase's signing key. Rotating SUPABASE_JWT_SECRET (which Supabase recommends periodically) would invalidate every outstanding iris-OAuth bearer. Bad operational coupling.
- iris-OAuth tokens then look like Supabase-issued tokens but with custom claims (`aud="iris-mcp"`, `azp`, `scope`). They aren't real Supabase tokens — they'd never validate against Supabase's own `/auth/v1/*` endpoints — but they share the same signing trust. Confusing security boundary.
- The hybrid approach makes the issuer/validator pair symmetric: iris signs → iris validates. Supabase signs → Supabase validates. Clean separation.

## Why not fall through from iris validation to Supabase validation on signature failure

If a token with `aud="iris-mcp"` fails the iris-signature check, **return 401 immediately**. Don't try Supabase validation. Otherwise an attacker who possesses a valid Supabase-signed token could attach `aud="iris-mcp"` to it (no, they couldn't actually — the `aud` is part of the signed payload — but the broader principle holds): the iris-OAuth identity should require an iris-OAuth-signed token. Audience is a routing claim, signature is the security boundary.

## Consequences

- ~40 LOC added to `_get_current_user_supabase` for the hybrid branch.
- 3 new regression tests in `tests/test_auth/test_supabase_mode_oauth_token.py`:
  - iris-OAuth token (correct signature) validates via iris path → returns user dict.
  - iris-OAuth token with wrong signature → 401, no Supabase fall-through.
  - Supabase-shaped token (no `aud="iris-mcp"`) routes through Supabase path → returns user dict.
- 120/120 OAuth + auth tests pass.
- `render.yaml` updated with `IRIS_JWT_SECRET` env var; operator must set the value in the dashboard (sync: false).
- Version bump v6.0.13 → v6.0.14. Patch-level (auth-correctness fix).

## Verification

- After deploy + operator sets `IRIS_JWT_SECRET` in the dashboard, claude.ai retries the OAuth flow → sign in → consent → Allow → connector status goes to **Connected** → `create_collection` returns 200 with the new id (no more `auth_required` from iris-mcp).
- Render API logs show successful 200s on `/api/sets`, `/api/collections`, etc.

## See also

- [ADR-164](ADR-164-OAuth-2.1-for-MCP.md) — original OAuth 2.1 design that introduced the dual-key situation.
- [ADR-173](ADR-173-OAuth-Boolean-Column-Parameterisation.md) — the previous step on this critical-path chain.
- Issue [#119](https://github.com/cgbarlow/iris/issues/119) — eleven-revision fix history.
