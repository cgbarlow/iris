# SPEC-170-A: Return 401 + WWW-Authenticate on unauthenticated MCP requests

ADR: [ADR-170](../ADR-170-Require-Bearer-On-MCP-HTTP-Endpoint.md)

## Summary

Short-circuit `POST /` on iris-mcp's HTTP transport at the ASGI layer when no bearer token is present. Return HTTP 401 with `WWW-Authenticate: Bearer resource_metadata="..."`. That response is the canonical OAuth Discovery trigger per MCP 2025-06-18 + RFC 9728 — claude.ai's MCP client uses it to start the OAuth dance (fetch metadata, DCR, redirect-to-sign-in, exchange code for bearer, retry). Static / health endpoints stay anonymous.

## MCP changes

### `mcp/src/iris_mcp/http_main.py:mcp_asgi`

Before dispatching to the MCP SDK's `session_manager.handle_request`, extract the bearer from the request's `Authorization` header. If absent, emit a 401 response with the WWW-Authenticate header and return without touching the MCP layer:

```python
async def mcp_asgi(scope, receive, send):
    if scope["type"] != "http":
        return
    token = extract_bearer(scope.get("headers") or [])

    if not token:
        metadata_url = (
            os.environ.get("IRIS_MCP_PUBLIC_URL", iris_url).rstrip("/")
            + "/.well-known/oauth-protected-resource"
        )
        # Header value is latin-1 only — keep the prose ASCII.
        header = (
            f'Bearer resource_metadata="{metadata_url}", '
            'error="invalid_token", '
            'error_description="MCP requests require an OAuth 2.1 '
            'access token. Sign in to Iris via your MCP client\'s '
            'connector UI; Dynamic Client Registration (RFC 7591) '
            'handles client setup automatically (no client_id or '
            'client_secret required)."'
        )
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json"),
                (b"www-authenticate", header.encode("latin-1")),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": (
                b'{"error":"unauthorized",'
                b'"error_description":"Sign in to Iris via your '
                b'MCP client connector to use this resource."}'
            ),
        })
        return

    async with IrisClient(url=iris_url, token=token) as client, bind_client(client):
        await session_manager.handle_request(scope, receive, send)
```

The `metadata_url` reads `IRIS_MCP_PUBLIC_URL` (per ADR-169) so the resource_metadata pointer matches what the Protected Resource metadata document advertises.

### Endpoints that stay anonymous

The 401 gate is on the **ASGI mount at `/`** (the MCP JSON-RPC endpoint). FastAPI routes that are mounted *before* the catch-all stay anonymous because they handle the request without ever reaching `mcp_asgi`:

- `GET /info` — service identity / health.
- `GET /favicon.{ico,svg}` — branding asset.
- `GET /.well-known/oauth-protected-resource` — RFC 9728 metadata. Must be anonymous so the OAuth client can fetch it after seeing the 401.

## Removed

Anonymous HTTP read access via iris-mcp. CLI scripts that need anonymous reads should use the **stdio transport** (`iris-mcp` binary with `IRIS_TOKEN`) or talk to iris-api directly via the SDK. Frontend + iris-client public endpoints are unaffected. This trade-off is what unlocks claude.ai's OAuth flow — every working production hosted-MCP server requires auth uniformly.

## Tool-layer payload preserved

The `_auth_required_payload` JSON in `tools.py` remains as a defensive backstop for the "bearer is present but invalid/expired" case (a 401 from iris-api downstream). v6.0.10's 401 only fires when no bearer at all. The two paths cover the two states.

## Tests

### `mcp/tests/test_http_main.py`

New `TestAuthChallenge` class with 4 cases:

1. `test_post_root_without_bearer_returns_401` — bare POST / with no auth header → HTTP 401.
2. `test_401_includes_www_authenticate_with_resource_metadata` — header is `Bearer resource_metadata="<url ending in /.well-known/oauth-protected-resource>"`.
3. `test_401_resource_metadata_url_uses_public_url_when_set` — with `IRIS_MCP_PUBLIC_URL=https://iris-mcp.example.com`, the `resource_metadata` value matches.
4. `test_post_root_with_bogus_bearer_passes_through_to_mcp_layer` — bearer present (even invalid) → not 401 at the transport layer. MCP layer handles the invalid bearer via the iris-api 401 → tool-payload path.

The existing `test_post_root_does_not_307` is updated to acknowledge the v6.0.10 401 (asserts `!= 307` and `!= 405` — both still hold).

## Versioning

`mcp/pyproject.toml`: 6.0.9 → 6.0.10. `frontend/package.json` matched.

## Acceptance criteria

- [ ] `curl -i -X POST https://iris-mcp.onrender.com/` returns HTTP 401 + `WWW-Authenticate: Bearer resource_metadata="..."` with `error="invalid_token"` and a user-facing `error_description`.
- [ ] GET `/info`, `/favicon.*`, `/.well-known/oauth-protected-resource` continue to return 200 anonymously.
- [ ] claude.ai's MCP client now recognises the connector as OAuth-required and surfaces a "Sign in" button on the connector card. (Direct verification: a call from claude.ai now returns the OAuth re-authorization prompt rather than the tool-error string.)
- [ ] 168/168 MCP tests pass.
