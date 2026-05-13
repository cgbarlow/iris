# SPEC-169-A: Fix Authorization Server URL in Protected Resource metadata

ADR: [ADR-169](../ADR-169-OAuth-Metadata-URL-Fix.md)

## Summary

In iris-mcp's RFC 9728 Protected Resource metadata at `/.well-known/oauth-protected-resource`, source `authorization_server` from `IRIS_API_URL` (where the RFC 8414 AS metadata document and `/oauth/*` endpoints actually live), not from `IRIS_WEB_URL` (the frontend, which is a SvelteKit SPA that returns its `index.html` for unknown `/.well-known/*` paths). The `resource` field falls back to `IRIS_API_URL` too when `IRIS_MCP_PUBLIC_URL` isn't set. Add `IRIS_MCP_PUBLIC_URL=https://iris-mcp.onrender.com` to `render.yaml` so the live deployment correctly identifies the iris-mcp service in the `resource` field.

## MCP changes

### `mcp/src/iris_mcp/http_main.py:_protected_resource_metadata`

Replace the v6.0.0 → v6.0.8 logic that sourced both fields from `IRIS_WEB_URL`:

```python
# Before (BUGGY):
public_url = os.environ.get("IRIS_MCP_PUBLIC_URL", "").rstrip("/")
web_url = os.environ.get("IRIS_WEB_URL", iris_url).rstrip("/")
return build_resource_metadata(
    resource=public_url or web_url,
    authorization_server=web_url,                # ← broke OAuth discovery
)
```

with `IRIS_API_URL`-based sourcing:

```python
# After:
public_url = os.environ.get("IRIS_MCP_PUBLIC_URL", "").rstrip("/")
as_url = iris_url.rstrip("/")                    # iris_url == IRIS_API_URL
return build_resource_metadata(
    resource=public_url or as_url,
    authorization_server=as_url,
)
```

`IRIS_WEB_URL` is **no longer read** by the OAuth-metadata code path. Its purpose remains link decoration only (`web_url` fields on tool responses, since v5.6.1).

### Auth-required tool error wording

`mcp/src/iris_mcp/tools.py:_auth_required_payload`: rewrite the message to reflect the correct claude.ai UX flow. Old wording assumed claude.ai's connector UI had a manual OAuth toggle ("Configure → enable OAuth") — the actual flow auto-detects OAuth from Protected Resource metadata and surfaces a "Sign in" button. New wording:

- Explains the user does NOT enter `client_id` / `secret` (Dynamic Client Registration handles it).
- Tells the model to direct the user to "find the Iris connector and click 'Connect' / 'Sign in'".
- Advises re-adding the connector if no Sign-in button appears (forces OAuth re-discovery).
- `next_step` field changes from `configure_oauth_in_connector_settings` → `user_signs_in_via_mcp_client_connector_ui`.

Mirror the same wording in `mcp/src/iris_mcp/server_instructions.py:_FALLBACK_INSTRUCTIONS` (AUTH RECOVERY section) and in the canonical `docs/prompts/mcp-server-instructions.md`. Operator pastes the canonical body into `/admin/settings/ai` to override the seeded text.

### `render.yaml` for the iris-mcp service

Add `IRIS_MCP_PUBLIC_URL=https://iris-mcp.onrender.com` to the `envVars` list. Operator must add this manually in the Render dashboard for the existing service — Render Blueprint sync doesn't auto-apply env-var additions to running services (same gotcha hit again in v6.0.11 / v6.0.12). The code's fallback to `IRIS_API_URL` keeps the deployment functional until the env var is set; the `resource` field is then cosmetically `iris-api...` instead of `iris-mcp.onrender.com`.

## Tests

### `mcp/tests/test_oauth_resource.py`

Strengthen the existing `TestHttpMainEndpointMounted.test_metadata_endpoint_returns_200` to set `IRIS_WEB_URL` to a known wrong value and assert it does NOT leak into either `resource` or `authorization_servers`:

```python
monkeypatch.setenv("IRIS_WEB_URL", "https://wrong-host.example.com")
# ...
assert body["resource"] == "https://iris-mcp.example.com"
assert body["authorization_servers"] == ["https://iris-backend.example.com"]
assert "wrong-host" not in body["resource"]
assert "wrong-host" not in body["authorization_servers"][0]
```

Add a fallback-shape test: without `IRIS_MCP_PUBLIC_URL`, both `resource` and `authorization_server` fall back to `IRIS_API_URL`.

### Existing tests

The `next_step` rename (`configure_oauth_in_connector_settings` → `user_signs_in_via_mcp_client_connector_ui`) breaks two existing test cases in `test_tools_create.py` and `test_tools_create_diagram.py`. Sed-replace to the new value.

## Versioning

`mcp/pyproject.toml`: 6.0.8 → 6.0.9. `frontend/package.json` matched.

## Acceptance criteria

- [ ] `curl https://iris-mcp.onrender.com/.well-known/oauth-protected-resource` returns `authorization_servers: ["https://iris-api-gtb3.onrender.com"]`.
- [ ] After operator adds `IRIS_MCP_PUBLIC_URL` in the Render dashboard for iris-mcp: `resource` reads `https://iris-mcp.onrender.com`. Without it, `resource` falls back to the API host (functional but cosmetically wrong).
- [ ] `IRIS_WEB_URL` does not appear in the OAuth metadata output for any combination of env settings.
- [ ] `auth_required` tool payload renders the v6.0.9 wording (no "Configure → enable OAuth"; explicit "no client_id/secret").
- [ ] 164/164 MCP tests pass.
- [ ] claude.ai → tap Sign in on Iris connector → browser opens to a host that returns OAuth metadata JSON (no SPA HTML). Without v6.0.10's 401 trigger this won't actually start the OAuth dance yet — that's the next ADR's spec.
