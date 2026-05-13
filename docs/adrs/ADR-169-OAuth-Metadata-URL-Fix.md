# ADR-169: Fix Authorization Server URL in Protected Resource metadata

Status: Accepted (2026-05-13)
Extends: [ADR-134](ADR-134-Standalone-MCP-HTTP-Service.md), [ADR-164](ADR-164-OAuth-2.1-for-MCP.md)

## Context

ADR-164 (v6.0.0) brought OAuth 2.1 to iris-mcp's HTTP transport: RFC 8414 Authorization Server metadata + RFC 9728 Protected Resource metadata + RFC 7591 Dynamic Client Registration + PKCE Authorization Code Flow. The intent was that any compliant MCP client (claude.ai, Claude Desktop, Claude Code, Cursor) could connect to iris-mcp and discover the OAuth endpoints automatically — no manual `client_id`/`secret` entry, no out-of-band configuration.

Issue #119 testing post-v6.0.8 surfaced a concrete failure. A write tool call from claude.ai returned the `auth_required` tool error, and claude.ai never offered the user a sign-in popup. Investigating the metadata chain:

```bash
$ curl https://iris-mcp.onrender.com/.well-known/oauth-protected-resource
{
  "resource": "https://iris-uat.chrisbarlow.nz",
  "authorization_servers": ["https://iris-uat.chrisbarlow.nz"],
  ...
}

$ curl https://iris-uat.chrisbarlow.nz/.well-known/oauth-authorization-server
HTTP 200
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    ...   # SvelteKit SPA index.html
```

The Protected Resource metadata advertises `https://iris-uat.chrisbarlow.nz` (the **frontend** host) as the Authorization Server. But the actual RFC 8414 AS metadata document and the `/oauth/{authorize,token,register,revoke}` endpoints live on the **API** host (`https://iris-api-gtb3.onrender.com`). The frontend host is a SvelteKit SPA configured with `adapter-static` + `fallback: 'index.html'`, so it returns HTTP 200 with the SPA index.html for any unknown path — including `/.well-known/oauth-authorization-server`.

The OAuth discovery chain breaks silently at step 4 (AS metadata fetch). claude.ai's MCP client can't parse OAuth metadata out of an HTML body, and falls back to surfacing the tool-layer `auth_required` error to the model. The user sees the model's "obtuse" advisory message instead of a one-click sign-in popup.

Root cause in `mcp/src/iris_mcp/http_main.py`:

```python
# v6.0.0 → v6.0.8 (BUGGY):
web_url = os.environ.get("IRIS_WEB_URL", iris_url).rstrip("/")
return build_resource_metadata(
    resource=public_url or web_url,         # falls back to frontend
    authorization_server=web_url,           # always uses frontend
)
```

`IRIS_WEB_URL` is the **frontend** host, used elsewhere for entity `web_url` link decoration (so the model can quote real iris-uat URLs). That's the right purpose for those tool responses, but it's the wrong source for OAuth metadata.

## Decision

In the Protected Resource metadata endpoint at `/.well-known/oauth-protected-resource`:

- `authorization_server` is sourced from **`IRIS_API_URL`** (the iris-backend host where the AS metadata document and `/oauth/*` endpoints live).
- `resource` falls back to `IRIS_API_URL` when `IRIS_MCP_PUBLIC_URL` isn't set (same host as the AS — a sensible dev default). Operators set `IRIS_MCP_PUBLIC_URL` in production to the canonical iris-mcp public URL.
- `IRIS_WEB_URL` is **no longer read** by the OAuth metadata path. Its purpose is link decoration only.

Add `IRIS_MCP_PUBLIC_URL = https://iris-mcp.onrender.com` to `render.yaml` for the iris-mcp service so the live deployment advertises the correct canonical resource URL.

Refine the tool-layer `auth_required` payload to give the user the right next-action wording. The previous "Configure → enable OAuth" framing assumed claude.ai's connector UI exposes a manual OAuth toggle; in the current flow the connector auto-detects OAuth from Protected Resource metadata and offers a "Sign in" button. The message now reflects that the user does **not** enter a `client_id` or `secret`, and that re-adding the connector forces metadata re-discovery if no sign-in button appears.

Update the canonical `mcp_server_instructions` paste-doc (`docs/prompts/mcp-server-instructions.md`) to match. Admin pastes this on UAT; the v6.0.5 TTL refresh propagates the body to claude.ai within 60 seconds.

## What changes for users

- After v6.0.9 deploys, adding the Iris connector in claude.ai should automatically display a "Sign in" button. Clicking it opens a browser tab; the user signs in to Iris; consent screen; redirect; bearer token stored by claude.ai. No `client_id` / `secret` entry required (RFC 7591 DCR handles the registration silently).
- Read tools (`search`, `get_*`, `list_*`, `package_hierarchy`) continue to work without sign-in. Only write tools (`create_*`, `update_*`) require it.
- If a user already had the Iris connector added pre-v6.0.9 and never saw a sign-in flow, they should remove and re-add it once v6.0.9 is live so the connector re-discovers the now-correct OAuth metadata.

## Why not also fix the upstream `oauth-authorization-server` proxy

Considered: have the frontend (`iris-uat.chrisbarlow.nz`) proxy `/.well-known/oauth-authorization-server` requests to the API host. That would make either host work. Rejected:

- Adds frontend complexity (SvelteKit `adapter-static` doesn't proxy; we'd need an explicit redirect or a non-static handler).
- Doesn't fix the `resource` field — that's still wrong unless we also change `http_main.py`.
- The simpler fix is to advertise the correct host in the first place.

## Consequences

- One `http_main.py` change (4 lines).
- One `render.yaml` change (one new env var).
- Three new test cases pinning the metadata correctness.
- Auth-recovery wording updated in three places — the canonical paste-doc, the iris-mcp hardcoded fallback, the tool-layer error payload. The admin re-pastes the canonical doc into `/admin/settings/ai`; the TTL refresh propagates.
- Version bump v6.0.8 → v6.0.9. Patch-level (config fix, no API surface change).

## See also

- [ADR-164](ADR-164-OAuth-2.1-for-MCP.md) — original OAuth 2.1 design that this fixes a deployment bug in.
- [ADR-134](ADR-134-Standalone-MCP-HTTP-Service.md) — the standalone iris-mcp HTTP service where the metadata is served.
- RFC 9728 — OAuth 2.0 Protected Resource Metadata.
- RFC 8414 — OAuth 2.0 Authorization Server Metadata.
- RFC 7591 — OAuth 2.0 Dynamic Client Registration.
- Issue [#119](https://github.com/cgbarlow/iris/issues/119) — original regression that surfaced this and several other related issues.
