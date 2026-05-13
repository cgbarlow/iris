# ADR-170: Require OAuth bearer on the MCP HTTP endpoint — return 401 + WWW-Authenticate

Status: Accepted (2026-05-13)
Extends: [ADR-164](ADR-164-OAuth-2.1-for-MCP.md), [ADR-169](ADR-169-OAuth-Metadata-URL-Fix.md)

## Context

ADR-164 (v6.0.0) shipped OAuth 2.1 for iris-mcp's HTTP transport: DCR (RFC 7591), PKCE Authorization Code Flow, Protected Resource metadata (RFC 9728), Authorization Server metadata (RFC 8414). ADR-169 (v6.0.9) fixed the metadata URLs to point at the right hosts.

After v6.0.9 deployed:

- `/info` → `version: 6.0.9` ✓
- `/.well-known/oauth-protected-resource` → correct `resource` and `authorization_servers` ✓
- `/.well-known/oauth-authorization-server` (on iris-api) → correct AS metadata ✓
- `POST /oauth/register` → DCR works, returns `client_id` with no `client_secret` ✓
- `POST / { "method": "initialize" }` (no bearer) → **HTTP 200** ✗

That last response is the root cause of the user-visible OAuth break. The MCP authorization spec (https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization) and RFC 9728 are explicit:

> MCP servers using authorization MUST include a `WWW-Authenticate` header when returning a `401 Unauthorized` to indicate the location of the resource server metadata URL...

> When a 401 response is received with a `WWW-Authenticate` header, the MCP client MUST parse the `resource_metadata` URL, fetch the Protected Resource Metadata, use the `authorization_server` URL to discover OAuth endpoints, initiate OAuth 2.1 Authorization Code Flow with PKCE, and retry the original request with the bearer token.

**The HTTP-401-with-WWW-Authenticate response is the canonical OAuth-Discovery trigger.** Without it, claude.ai's MCP client has no signal to start the OAuth dance — it adds the connector successfully (initialize works), marks it as anonymous, and never displays a "Sign in" button. The user clicks `create_collection` later; iris-mcp's tool-layer returns its custom `auth_required` JSON body (HTTP 200); claude.ai's model surfaces the message verbatim to the user. They follow the on-screen advice ("go to Connectors → Iris → Configure → enable OAuth") and find no such toggle, because claude.ai never registered the connector as OAuth-capable.

v6.0.0 → v6.0.9 all shipped this gap. The OAuth machinery is wired end-to-end but the **trigger** is missing.

## Decision

Make the iris-mcp HTTP endpoint at `POST /` return spec-compliant HTTP 401 with `WWW-Authenticate: Bearer resource_metadata="<PR metadata URL>", error="invalid_token", error_description="..."` whenever the request lacks a bearer token.

- The check is at the **transport** layer in `mcp_asgi` (in `http_main.py`), short-circuiting before the JSON-RPC dispatcher runs.
- The `resource_metadata` URL is constructed from `IRIS_MCP_PUBLIC_URL` (when set) or `IRIS_API_URL` (fallback), matching ADR-169's URL sourcing.
- Static/health endpoints (`/info`, `/favicon.{ico,svg}`, `/.well-known/oauth-protected-resource`) stay anonymous; only the MCP JSON-RPC mount requires auth.

## What changes for users

- **claude.ai now displays a "Sign in" button on the Iris connector.** When the user adds iris-mcp via Settings → Connectors, claude.ai's connector probe gets back HTTP 401 with the resource_metadata pointer, fetches the metadata, registers itself via DCR, and surfaces the OAuth-required state in the UI. Clicking "Sign in" opens a browser tab against `/oauth/authorize` on the iris-api host; user signs in to Iris; OAuth code exchanged for a bearer; bearer attached to all subsequent MCP requests.
- **Anonymous HTTP read access via iris-mcp is removed.** A CLI script that wants to call iris-mcp's HTTP endpoint without OAuth must now use the stdio transport (`iris-mcp` with `IRIS_TOKEN`) or talk to iris-api directly. The frontend's read-only public endpoints and the iris-client SDK paths are unaffected.

## Why not selectively 401 only on writes

Considered: parse the JSON-RPC body, sniff for tools/call + write-tool names, return 401 only there. Rejected:

- Adds 30+ LoC of body parsing on every request hot path.
- Doesn't actually solve the connector-setup UX: claude.ai still wouldn't see a 401 at connector-add time (when only `initialize` runs), so the "Sign in" button wouldn't surface until the user's first write attempt. That's exactly the bad UX we're trying to fix.
- The MCP spec doesn't condition the 401 on operation type — it conditions on credentials present.

Requiring auth uniformly for the MCP endpoint is simpler, spec-aligned, and matches what every other production hosted-MCP server does (Linear, Atlassian, GitHub remote MCP).

## Why a transport-layer short-circuit (not a per-tool decorator)

- Single source of truth for the auth-challenge response. Every tool inherits the same 401 + `WWW-Authenticate` shape automatically.
- Body parsing isn't needed.
- The MCP SDK is left untouched; we're not racing the SDK's own JSON-RPC machinery for response-construction order.

## Why `error="invalid_token"` (not `error="invalid_request"`)

RFC 6750 §3.1: `invalid_token` is the canonical error for "request didn't carry an access token, or the token was invalid / expired". `invalid_request` is for malformed Authorization headers. We're rejecting the "no token at all" case, which OAuth treats as `invalid_token` per most resource-server implementations (and per the wording in MCP authorization references).

## Consequences

- ~50 LOC added to `http_main.py:mcp_asgi`: extract bearer, short-circuit with 401 if absent.
- Existing 12 `test_http_main.py` cases stay green (they cover anonymous endpoints, not the JSON-RPC mount).
- 4 new `TestAuthChallenge` cases pin the 401 response shape, the WWW-Authenticate header, the resource_metadata URL sourcing, and the "bearer present → pass through" behaviour.
- The tool-layer `auth_required` JSON payload in `tools.py` is preserved as a defensive backstop — if a request arrives with an invalid (not just missing) bearer, the backend's 401 still bubbles up through the existing path. v6.0.10 doesn't change that path; it only fixes the missing-bearer case.
- Version bump v6.0.9 → v6.0.10. Patch-level (transport-protocol compliance fix, no new MCP tool surface).

## Verification

- 168/168 MCP tests pass locally.
- Post-deploy, curl confirms:
  - `POST /` with no bearer → HTTP 401, `WWW-Authenticate: Bearer resource_metadata="https://iris-mcp.onrender.com/.well-known/oauth-protected-resource", error="invalid_token", ...`
  - `POST /` with bearer → passes to the MCP SDK as before.
- Remove + re-add Iris connector in claude.ai → a "Sign in" button appears on the connector → clicking opens the OAuth flow → user signs in → write tools succeed.

## See also

- [ADR-164](ADR-164-OAuth-2.1-for-MCP.md) — original OAuth 2.1 design.
- [ADR-169](ADR-169-OAuth-Metadata-URL-Fix.md) — corrected the metadata URLs this ADR's 401 points at.
- RFC 9728 — OAuth 2.0 Protected Resource Metadata (§5.1 WWW-Authenticate Response).
- RFC 6750 — Bearer Token Usage (§3 WWW-Authenticate).
- MCP Authorization Spec — https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization
- Issue [#119](https://github.com/cgbarlow/iris/issues/119) — seven-revision fix history (v6.0.4 → v6.0.10) culminating in this transport-layer fix.
