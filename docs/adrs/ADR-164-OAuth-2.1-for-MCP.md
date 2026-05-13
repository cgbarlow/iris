# ADR-164: OAuth 2.1 for iris-mcp HTTP transport; remove pairing-code flow

Status: Accepted (2026-05-13)
Supersedes: [ADR-160](ADR-160-MCP-Pairing-Code-Authentication.md)
Extends: [ADR-127](ADR-127-Personal-Access-Tokens.md), [ADR-131](ADR-131-MCP-Server-Architecture.md), [ADR-134](ADR-134-Standalone-MCP-HTTP-Service.md)

## Context

v5.15.0 (ADR-160) introduced the pairing-code + `iris_authenticate` MCP tool to let users authenticate write tools from inside a conversation. The design works in **stdio** mode but is **fundamentally broken in HTTP-streamable mode** — the only transport claude.ai's hosted-MCP feature supports.

Root cause (verified during v5.18.0 testing):

- `mcp/src/iris_mcp/http_main.py:101-110` creates a fresh `IrisClient` per HTTP request, with whatever bearer is in that request's headers.
- `mcp/src/iris_mcp/asgi.py:79-96` uses `StreamableHTTPSessionManager(stateless=True)` — no MCP-level session affinity.
- `_iris_authenticate` calls `c.set_token(...)` on the **ephemeral per-request client**; the mutation dies at request boundary.
- The persisted `~/.iris-mcp/<hash>.json` token file is written on the iris-mcp service's filesystem (shared across all users) and never read in HTTP mode.

The pairing flow cannot work in HTTP without breaking multi-user safety — any persistence we add would leak tokens across user sessions. v5.17.0's regression test covered the stdio path; HTTP was uncovered.

The MCP specification (2025-06-18) mandates OAuth 2.1 for HTTP-transport MCP servers (RFC 8414 AS metadata + RFC 9728 resource metadata + RFC 7591 DCR + PKCE Authorization Code Flow). claude.ai performs the OAuth dance automatically once a server advertises it. This is the correct architecture.

## Decision

**Replace** the pairing-code mechanism with full OAuth 2.1 for the iris-mcp HTTP transport.

- **Authorization Server**: iris-backend (owns user identity).
- **Protected Resource**: iris-mcp (HTTP transport only).
- **Token format**: JWT access tokens signed with the existing `JWT_SECRET` (HS256), validated by the existing `get_current_user` dependency. Opaque DB-stored refresh tokens with family-id rotation/theft detection.
- **Scope model**: single `iris` scope = full access (matching the current PAT model).
- **Dynamic Client Registration**: open per RFC 7591 — any MCP client can register without admin pre-approval. User authorisation gates access, not client_id allocation.
- **Consent**: explicit consent screen at `/oauth/authorize` after the user signs in. `client_name` rendered with DOMPurify (protocol §7) since DCR-supplied content is untrusted.

**Stdio transport is unchanged.** Operators continue to set `IRIS_TOKEN` env var (a PAT issued from `/settings/tokens`). The MCP spec OAuth flow assumes HTTP; stdio MCP clients (Claude Desktop with stdio config) don't perform an OAuth handshake — env-var bearer is the standard pattern.

**PATs are kept** for CLI / scripted use. The `personal_access_tokens` table, `/api/users/me/tokens` endpoints, and `verify_pat` machinery are unchanged. `iris_pat_*` bearer detection continues to coexist with OAuth-issued JWT bearers in `get_current_user`.

**`save_doview_analysis`** (deprecated since v5.17.0 per ADR-162) is removed. Replacement is `create_diagram(notation='markdown', diagram_type='doview_analysis', ...)`.

## Why HS256 with the existing JWT_SECRET (not RS256 + JWKS)

- iris-backend and iris-mcp are deployed by the same operator and can share a secret via env vars (already do for the v1 `/api/auth/login` JWT flow).
- HS256 validation has zero network cost — `get_current_user` already does it.
- RS256 + JWKS adds an HTTP fetch (or an in-memory cache + refresh schedule) and a separate key-rotation discipline. Useful for federated multi-tenant deployments; overkill for single-instance Iris.
- If a future deployment shape requires it (e.g. third-party auth servers), bumping to RS256 is a localized backend change behind the existing dependency boundary.

## Why JWT access tokens (not DB-stored opaque tokens)

- Stateless validation — every iris-backend request (and every iris-mcp request that proxies through) needs the user identity. JWT validation has no DB hit.
- Revocation is handled by refresh tokens being DB-stored and revokable; access tokens have a 1-hour lifetime, so worst-case loss-of-control is bounded.
- Pattern matches the existing `/api/auth/login` flow — consistent and reviewable.

## Why open Dynamic Client Registration

- The MCP spec mandates DCR support. Required if we want any new MCP client (claude.ai, Cursor, Windsurf, future ones) to integrate without per-operator pre-approval.
- The threat model is **user authorisation**, not client ID allocation. An unauthorised client_id with no user grant is useless — it can't get an access token.
- Admin visibility: registered clients appear in audit logs / admin UI (future) so an operator can revoke a misbehaving client if needed. v6.0.0 just stores the rows; v6.1+ can add the admin UI.

## Why explicit consent screen (not auto-approve)

- Standard OAuth UX: the user knows which third-party client is being authorised.
- Audit trail: consent decision is logged with the auth code.
- Allows the user to deny if they didn't initiate the request (CSRF defence, even with `state`).
- Minor UX cost — one extra page in the dance; standard for every consumer OAuth flow.

## Consequences

- New backend module `app/oauth/` with five endpoints.
- New tables: `oauth_clients`, `oauth_authorization_codes`, `oauth_refresh_tokens`.
- `pairing_codes` table dropped; pairing endpoints removed; pairing UI removed.
- `iris_authenticate` MCP tool removed; `~/.iris-mcp/<hash>.json` store removed; `set_token` IrisClient method removed.
- `save_doview_analysis` MCP tool removed.
- New iris-mcp `/.well-known/oauth-protected-resource` endpoint + `WWW-Authenticate` header on 401.
- New frontend `/oauth/authorize` consent screen.
- ~43 new tests; ~30 tests removed (pairing flow tests).
- Breaking changes: HTTP/claude.ai users must (re)configure their connector to use OAuth; stdio users with `IRIS_TOKEN` unchanged; any caller of `save_doview_analysis` by name must migrate to `create_diagram`.

## Out of scope (deferred)

- OAuth on stdio transport — env-var bearer is the standard pattern; OAuth dance requires HTTP.
- OpenID Connect — pure OAuth 2.1; `sub` claim is sufficient.
- Scope refinement beyond `iris` — split into `iris:read` / `iris:write` later if real demand surfaces.
- RS256 + JWKS — single-instance HS256 is sufficient.
- Admin UI for revoking OAuth clients / sessions — v6.1+.
- Multi-tenant / federated identity — v6.x+ if needed.

## See also

- [ADR-127](ADR-127-Personal-Access-Tokens.md) — PAT machinery (kept for CLI).
- [ADR-131](ADR-131-MCP-Server-Architecture.md) — iris-mcp architecture.
- [ADR-134](ADR-134-Standalone-MCP-HTTP-Service.md) — iris-mcp HTTP transport.
- [ADR-160](ADR-160-MCP-Pairing-Code-Authentication.md) — superseded; pairing flow.
- [ADR-162](ADR-162-Generic-MCP-Diagram-Creation-Workflow.md) — `create_diagram` replaces `save_doview_analysis`.
- [SPEC-164-A](specs/SPEC-164-A-OAuth-2.1-for-MCP.md) — endpoint shapes, schema, MCP wiring, consent screen, test plan.
- MCP spec, OAuth: https://modelcontextprotocol.io/specification/draft/basic/authorization
- RFC 6749 (OAuth 2.0), RFC 7591 (DCR), RFC 7636 (PKCE), RFC 8414 (AS metadata), RFC 9728 (Resource metadata).
