# SPEC-134-A: iris-mcp Standalone Service

ADR: [ADR-134](../ADR-134-MCP-Standalone-Service.md)

## Surface

A separate Render web service named `iris-mcp` that runs:

```
uvicorn iris_mcp.http_main:create_app --factory --host 0.0.0.0 --port $PORT
```

Endpoints:

| Method | Path | Purpose |
|---|---|---|
| `POST` `GET` `DELETE` | `/` (bare hostname) | MCP Streamable HTTP (root mount) |
| `GET` | `/favicon.{ico,svg}` | The Iris eye favicon (same SVG as ADR-133) |
| `GET` | `/info` | `{"service": "iris-mcp", "endpoint": "/", "backend": "..."}` for humans / health |

The standalone service is MCP-only, so the protocol lives at the root
rather than at `/mcp`. The `/info` route is at a non-conflicting path
because Streamable HTTP itself uses `GET /` for session resumption
and streaming notifications.

## Configuration

| Env var | Required | Purpose |
|---|---|---|
| `IRIS_API_URL` | yes | Backend URL the service proxies through, e.g. `https://iris-api-gtb3.onrender.com`. Service refuses to start if unset. |
| `PORT` | (Render sets) | Listen port |

## 307 fix (embedded path only)

The standalone service mounts MCP at `/` so there's no slash-redirect
to chase. The embedded mount on the iris backend keeps `/mcp` as its
namespace (it shares the host with `/api/*`); FastAPI's default
`redirect_slashes` would 307 bare `/mcp` to `/mcp/`, and some MCP
clients drop POST bodies on a 307. Fix in the embedded path only: a
tiny middleware that rewrites `/mcp` → `/mcp/` in the ASGI scope
before routing.

## DRY

`_extract_bearer(headers)` lives in **one** place:
`iris_mcp/asgi.py`. Both `iris_mcp/http_main.py` (standalone) and
`backend/app/mcp_route.py` (embedded) import it. Branding asset
(`ICON_SVG`) likewise — already centralised in `iris_mcp.branding`.

## Embedded mount becomes opt-in

`backend/app/mcp_route.attach_mcp(app)` no-ops unless
`IRIS_EMBEDDED_MCP=1`. Production sets `IRIS_EMBEDDED_MCP=0` (or
omits the var) so the backend doesn't carry the MCP SDK in memory.
Local dev defaults `IRIS_EMBEDDED_MCP=1` for one-process convenience.

## Render service block (render.yaml)

```yaml
- type: web
  name: iris-mcp
  runtime: docker
  plan: free
  region: singapore
  dockerfilePath: mcp/Dockerfile
  dockerContext: .
  envVars:
    - key: IRIS_API_URL
      value: https://iris-api-gtb3.onrender.com   # iris-api Render-assigned URL
```

## Dockerfile (mcp/Dockerfile)

Minimal Python 3.12 image — installs `iris-client`, `iris-mcp`, and
uvicorn, and runs `iris_mcp.http_main:create_app`.

## Tests

- `mcp/tests/test_http_main.py`:
  1. `create_app()` raises if `IRIS_API_URL` is unset.
  2. `GET /info` returns service identity JSON.
  3. `GET /favicon.{ico,svg}` returns the SVG (and isn't swallowed
     by the root mount — order matters in the FastAPI app).
  4. `POST /` is handled by the MCP mount, not 307'd, not 405'd.

## Acceptance

- Render dashboard shows two healthy services: `iris-api` and
  `iris-mcp`. Both stay under their 512 MB allocations.
- `https://iris-mcp-<suffix>.onrender.com` (bare) returns a valid MCP
  `initialize` response with `serverInfo.icons` populated.
- Adding the URL to Claude Desktop's connector UI works.
- `iris-api` is no longer carrying the MCP SDK in resident memory
  unless explicitly enabled via `IRIS_EMBEDDED_MCP=1`.
- The 307 round-trip on bare `/mcp` is gone (single 200, no redirect).
