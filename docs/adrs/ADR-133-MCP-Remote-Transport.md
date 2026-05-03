# ADR-133: HTTP Remote Transport for iris-mcp

Status: Accepted (2026-05-04)

## Context

[ADR-131](ADR-131-MCP-Server-Architecture.md) chose stdio as iris-mcp's
only transport, on the basis that "every current MCP client installs
servers that way." That was true at the design moment, and remains the
right answer for *power users* on machines they fully control. But
real-user feedback while installing iris-mcp into Claude Desktop on a
corporate-managed Windows laptop hit, in order:

1. `uvx` not on `PATH` — install uv.
2. uv installed but PATH not refreshed in Claude Desktop's child
   process — give the absolute `.exe` path.
3. uv now invokes git to clone the repo — corporate proxy / cert
   intercept makes `git fetch` fail inside uv (which uses libgit, not
   the user's git config).
4. `claude_desktop_config.json` lives in `%APPDATA%\Claude\` — the user
   has to find and edit it.
5. Claude Desktop must be fully quit (system-tray Quit, not close-
   window) before changes take effect.

Each step is a paper cut; together they kill the "I just want to try
it" moment. Meanwhile Claude Desktop's *Manage Connectors* UI accepts
a URL — paste, name, done — but only for **remote** MCP servers.

## Decision

Add an **HTTP (Streamable HTTP) transport** to iris-mcp, mounted on the
existing iris backend at **`POST /mcp`**. End-user install becomes:

> Open Claude Desktop → Settings → Connectors → Add → paste
> `https://iris-uat.chrisbarlow.nz/mcp` → done.

Zero local install. Zero git. Zero JSON editing. Auth via an optional
Bearer token that the connector UI already supports.

The stdio transport from ADR-131 stays — it's still the right choice
for offline / sandboxed / per-user-scoped local use, and it's already
shipped.

## Why HTTP, not WebSocket / SSE only

The MCP spec's current "remote" recommendation is **Streamable HTTP**
(`POST /mcp` + chunked response for streaming). Claude Desktop's
connector UI expects exactly that shape. SSE-only and WebSocket
transports also exist in the SDK but are either deprecated (SSE) or
not yet first-class in Claude Desktop. We'll ship Streamable HTTP only;
SSE can be added later under the same `/mcp` mount if a client demands
it.

## Why mount on the backend, not host as a sidecar

Two reasons.

- **No new infrastructure.** The backend already owns iris's hostname,
  TLS cert, rate-limit middleware, audit log, anonymous-bypass policy
  (ADR-123), and CORS rules. A sidecar would re-implement all of these.
- **Auth alignment.** PATs (ADR-127) already travel as
  `Authorization: Bearer iris_pat_…` against the same hostname. Mounting
  `/mcp` on the same FastAPI app means MCP requests flow through the
  same auth dependency, the same `pat`/`anon` rate-limit buckets, and
  the same audit pipeline as the REST API — no parallel mechanism to
  keep in sync.

The trade-off is that the backend now has two protocol surfaces (REST
JSON + MCP Streamable HTTP) on one process. That's fine: both are HTTP,
both share the same auth/rate-limit middleware, and the MCP route is
opaque to the rest of the app (it's a single `Mount`).

## Why not just publish to PyPI and improve the stdio path

Publishing is in scope as a follow-up regardless. But even with PyPI
the stdio path still requires Python + a launcher (`uvx` / `pipx` /
`pip`) + JSON config + Claude Desktop restart. Publishing removes one
dependency (git) but not the rest. The remote-MCP path removes *all*
of them.

## Auth model (per-request)

The MCP server is built once at app startup with a *placeholder*
`IrisClient`. At each incoming MCP request the FastAPI route extracts
the `Authorization` header, constructs a per-request `IrisClient` with
the appropriate token (or anonymous), binds it into a `ContextVar`,
and the existing tool/resource dispatch code reads from that context.
Per-user isolation without rebuilding the MCP server.

## Rate-limit and audit

`POST /mcp` traverses the same middleware stack as `/api/*`:

| Caller | Bucket | Audit |
|---|---|---|
| Anonymous | `anon` (or `anon_ai` if the tool maps to an `/api/ai/*` call) | Logged with `username=anonymous` |
| PAT | `pat` | Logged with `username=<pat owner>` |

No new bucket needed. No new audit event type needed.

## Migration / compatibility

- Existing stdio installs (`docs/mcp.md` install instructions) keep
  working unchanged — same package, same entry point, additional ASGI
  app exported from the package.
- `docs/mcp.md` is rewritten to lead with **"add a connector by URL"**
  and demote the stdio install to a "for advanced/local use" note.
- No new env vars in production — the backend already serves on the
  hostname users will paste.

## Out of scope (deferred)

- OAuth2 dynamic client registration on the connector. PAT-as-bearer
  is the v1 auth path, matching every other iris surface.
- Per-tool RBAC beyond what already flows from PAT → user → role. If a
  user's role can call `POST /api/ai/sets/{id}/create-diagram/apply`,
  they can call the equivalent MCP tool. If they can't, they can't.
- WebSocket transport. Add if a client requires it.

## See also

- [ADR-131](ADR-131-MCP-Server-Architecture.md) — original stdio
  decision, kept in force for the local install path.
- [ADR-127](ADR-127-Personal-Access-Tokens.md) — PAT format and
  per-request auth dependency.
- [ADR-129](ADR-129-Public-HTTP-API-Stabilisation.md) — OpenAPI
  publishing (the MCP route is intentionally **excluded** from the
  OpenAPI schema; it's a different protocol).
- SPEC-133-A — implementation contract.
