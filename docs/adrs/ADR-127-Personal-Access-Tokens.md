# ADR-127: Personal Access Tokens for API Authentication

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-127 |
| **Initiative** | Agentic-AI-friendly API (Issue #21) |
| **Proposed By** | Engineering |
| **Date** | 2026-04-22 |
| **Status** | Proposed |

---

## ADR (WH(Y) Statement format)

**In the context of** Iris authenticating every request with a
short-lived (15-minute) JWT issued by either its own login endpoint
(SQLite mode, HS256) or by Supabase (Supabase mode) — a model that
works well for a human clicking through the SvelteKit frontend but
fails the new requirement (Issue #21) to let CLIs, MCP servers, and
autonomous AI agents use Iris as a programmable resource, because (a)
there is no way to mint a long-lived credential that can be pasted
into `~/.config/iris/config.toml`, a CI secret, or a Claude Desktop
`env` block; (b) the JWT refresh-token rotation flow is designed for a
browser with a cookie jar and cannot safely sit in a shell environment;
(c) there is no API-key / service-token / PAT concept anywhere in the
codebase today,

**facing** the need to give users a stable credential that (i) is
long-lived and revocable without rotating their password, (ii) carries
an audit trail distinct from an interactive login, (iii) inherits the
existing RBAC role model (Admin / Architect / Reviewer / Viewer, 26
permission mappings) with zero new authorisation code, (iv) can be
rate-limited independently from JWT-authenticated browser traffic and
anonymous traffic, and (v) can be adopted incrementally without
touching the existing JWT code path that the frontend depends on,

**we decided for** introducing a **Personal Access Token (PAT)**
concept — a new `personal_access_tokens` table keyed to a user,
storing only the Argon2id hash of a generated secret (same hasher used
for passwords per NZISM), plus a short indexable prefix, `created_at`,
`last_used_at`, optional `expires_at`, and `revoked_at`; the token is
emitted exactly once as `iris_pat_<prefix>_<secret>` (32 bytes of
urlsafe random in the secret portion); `get_current_user` /
`get_optional_user` are extended to recognise the `iris_pat_` prefix
on Bearer tokens and route to a PAT validator that looks up by prefix,
Argon2id-verifies the secret, rejects revoked/expired tokens, touches
`last_used_at`, and resolves to the same user dict shape as the JWT
path — so every downstream router, RBAC check, and service call
operates identically regardless of which credential authenticated the
request; a new rate-limit bucket `pat` is added so PAT-authenticated
requests can be tuned separately from `general` (JWT) and the
anonymous buckets introduced by ADR-123; management endpoints live at
`/api/users/me/tokens` (list, create, revoke), are caller-scoped only,
and are available in both SQLite and Supabase deployments,

**and neglected** (a) **OAuth2 / OIDC client-credentials flow** —
correct long-term answer for service-to-service auth, but requires a
full authorisation server, client registration UI, consent screens,
and JWKS rotation, which is an order of magnitude more work than v1
needs and not justifiable until there are external machine clients
consuming Iris; (b) **granular scopes** (e.g. `read`, `ai:ask`,
`ai:create`, `export`) — valuable for narrow-use agents but requires
changes to every router's authorisation middleware and a UI surface
for scope selection; deferred to a future ADR once real scope demand
is observed; (c) **JWT-only with long-lived refresh tokens** — keeps
the codebase smaller but puts a refresh token in a shell env var,
which is worse than a PAT for rotation, audit, and revocation; (d) a
**separate API-key table for service accounts** (decoupled from users)
— clean in theory but doubles the RBAC surface and forces admins to
manage a second set of identities; PAT-inherits-user-role reuses every
existing permission mapping; (e) **IP allow-lists on tokens** — a
defence-in-depth ask that is not necessary for v1 and can be layered
on later as a token attribute,

**to achieve** a bearer credential that agents, CLIs, and CI can use
with zero changes to the existing JWT path or frontend, a single
auth-dependency extension (one prefix check + one validator function)
that keeps the JWT code unchanged, reuse of the Argon2id hasher and
RBAC model already in production, a distinct audit trail (PAT
`last_used_at` vs. audit-log entries for JWT logins), and a natural
on-ramp to scoped tokens later without breaking v1 tokens,

**accepting that** a PAT silently inherits every permission of its
creating user (an Architect's PAT can do what an Architect can), which
is a footgun if a user loses their laptop — mitigated by (i) the
one-shot reveal of the secret, (ii) self-service revocation in
Settings, (iii) the `last_used_at` column making unused tokens easy
to audit, and (iv) the Argon2id hash ensuring a DB leak does not leak
usable secrets; accepting that PATs live only in the `main` DB (not in
the audit DB), so revoking a token is itself audited via the standard
audit-log entry emitted by the mgmt endpoint rather than the PAT table
being hash-chained; accepting that the rate-limit bucket adds one row
to the rate-limit config and one branch to the middleware — trivial.

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| PAT table | `personal_access_tokens` — id, user_id, name, token_hash (Argon2id), prefix (indexed), created_at, last_used_at, expires_at, revoked_at. Mirror table in Supabase with RLS (per ADR-095). | [SPEC-127-A](./specs/SPEC-127-A-Personal-Access-Tokens.md) |
| Token format | `iris_pat_<prefix>_<secret>` — 8-char prefix + 32-byte urlsafe secret. Emitted exactly once on creation. Argon2id hash persisted. | SPEC-127-A |
| Auth dependency | `get_current_user` / `get_optional_user` detect the `iris_pat_` prefix and route to a PAT validator; JWT path unchanged. Resolves to the same user dict. | SPEC-127-A |
| Rate-limit bucket | New `pat` bucket in `middleware/rate_limit.py`. Default 60/min (tunable). Separate from `general` (JWT) and `anon` / `anon_ai`. | SPEC-127-A |
| Mgmt endpoints | `GET/POST/DELETE /api/users/me/tokens`. Caller-scoped. Secret returned exactly once on create. | SPEC-127-A |
| Frontend | New Settings tab "API Tokens" — list (name, prefix, last-used, created), create dialog (copy-to-clipboard, one-shot warning), revoke with confirm. | SPEC-127-A |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-005 | RBAC Design | PATs inherit the creating user's role; no scope model in v1. |
| Depends On | ADR-095 | Row Level Security | PAT table in Supabase mode gets RLS (owner-only read/write). |
| Coordinates | ADR-123 | Anonymous Read-Only Bypass | PAT holders traverse `get_optional_user` just like JWT holders; anonymous callers remain anonymous. |
| Enables | ADR-129 | Public HTTP API Stabilisation | PATs are the auth mechanism documented in the public API docs. |
| Enables | ADR-130 | CLI Architecture | `iris login` creates a PAT and stores it locally. |
| Enables | ADR-131 | MCP Server Architecture | `IRIS_TOKEN` env var carries a PAT to the stdio MCP server. |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-127-A | Personal Access Tokens Implementation | Technical Specification | [specs/SPEC-127-A-Personal-Access-Tokens.md](./specs/SPEC-127-A-Personal-Access-Tokens.md) |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-04-22 |
