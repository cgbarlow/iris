# SPEC-133-A: HTTP Remote Transport for iris-mcp

ADR: [ADR-133](../ADR-133-MCP-Remote-Transport.md)

## What it is

A FastAPI route at `POST /mcp` that speaks **MCP Streamable HTTP** to
remote clients (Claude Desktop's "Manage Connectors" UI, Cursor's
remote-MCP support, custom agents). Wraps the existing `iris_mcp.tools`
and `iris_mcp.resources` modules — the dispatch logic is unchanged.

## Surface

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/mcp` | MCP JSON-RPC requests over HTTP. Streamable response per the MCP spec. |
| `GET` | `/mcp` | Health/handshake endpoint per Streamable HTTP. |
| `DELETE` | `/mcp` | Session teardown per Streamable HTTP. |

Excluded from the public OpenAPI schema (separate protocol; ADR-129
docs cover REST, this spec covers MCP).

## Auth

- Read `Authorization: Bearer …` from the request.
- If header is `iris_pat_…`: validate via the existing `_get_current_user_pat`
  dependency. If invalid: 401.
- If header is a JWT: validate via the existing JWT dependency. If
  invalid: 401.
- If header is absent: anonymous (subject to `anon`/`anon_ai` rate-limit
  buckets exactly as elsewhere).
- Per-request: build an `IrisClient` configured with the same token,
  pointing at the in-process backend (via `httpx.ASGITransport(app)`,
  so MCP→backend traffic doesn't leave the process).

## Per-request client binding

The lowlevel `mcp.server.Server` instance is built once at app startup.
Tool dispatch handlers receive an `IrisClient`. To make that
per-request without rebuilding the server, use a `ContextVar`:

```python
# iris_mcp/asgi.py
_current_client: ContextVar[IrisClient] = ContextVar("iris_client")

def get_current_client() -> IrisClient:
    return _current_client.get()
```

The FastAPI route sets the var per request:

```python
@router.post("/mcp", include_in_schema=False)
async def mcp_endpoint(request: Request):
    token = _extract_bearer(request)
    async with IrisClient(url=..., token=token, transport=...) as client:
        token = _current_client.set(client)
        try:
            return await session_manager.handle_request(...)
        finally:
            _current_client.reset(token)
```

`iris_mcp.server.build_server` is updated to read from
`get_current_client()` inside `_call_tool` / `_read_resource` rather
than from a closure.

## Rate-limit

`/mcp` is matched by the existing rate-limit middleware. Bucket
selection (`pat` / `anon` / `anon_ai`) follows the same rules as `/api/*`
endpoints: by auth type and by whether the called tool maps to an AI
endpoint. No new buckets.

## Tests

- **Smoke** (`backend/tests/test_mcp_route.py`):
  1. `POST /mcp` with `initialize` request returns a valid Streamable
     HTTP response with capabilities.
  2. `POST /mcp` with `tools/list` returns the same 19 tools as the
     stdio server.
  3. `POST /mcp` with `tools/call` for `search` against an empty
     repository returns a result containing `query`.
  4. Anonymous request to a privileged tool (e.g. PAT-mgmt) returns
     a structured error, not a crash.
- **Per-request auth** (`mcp/tests/test_asgi.py`):
  1. Anonymous request: `_current_client` resolves to a token-less
     `IrisClient`.
  2. PAT request: `_current_client` resolves to a token-bound
     `IrisClient` whose `whoami()` returns the PAT owner.
  3. Invalid PAT: 401, no client constructed.

## File touch list

### Add
- `mcp/src/iris_mcp/asgi.py` — `build_asgi_app(client_factory)`,
  `get_current_client()`, ContextVar plumbing.
- `backend/app/mcp_route/__init__.py` (or inline in `main.py`) —
  FastAPI mount of the MCP ASGI app at `/mcp`.
- `backend/tests/test_mcp_route.py` — end-to-end smoke.
- `mcp/tests/test_asgi.py` — per-request binding.

### Modify
- `mcp/src/iris_mcp/server.py` — `build_server` no longer closes over
  a single `IrisClient`; reads from the ContextVar at dispatch time.
- `backend/app/main.py` — mount the MCP ASGI app, wire the
  per-request auth.
- `docs/mcp.md` — rewrite to lead with "add a connector by URL"; demote
  stdio to a "local-only" appendix.

### Leave alone
- `mcp/src/iris_mcp/__main__.py` — stdio entry point unchanged.
- `mcp/src/iris_mcp/tools.py`, `resources.py` — dispatch tables
  unchanged. The injected `IrisClient` parameter is now sourced from
  the ContextVar in HTTP mode and from the closure in stdio mode; the
  function signature doesn't change.

## Acceptance

- A user pastes `https://iris-uat.chrisbarlow.nz/mcp` into Claude
  Desktop's connector UI, with no other configuration, and the iris
  tools appear in a new chat — anonymous mode.
- A user adds the same URL with a PAT in the connector's auth field
  and the same tools appear, but with their role's permissions
  applied (e.g. PAT-mgmt tools work).
- The stdio install path from ADR-131 / SPEC-131-A continues to work
  with no documentation change required to the existing JSON config
  examples.
