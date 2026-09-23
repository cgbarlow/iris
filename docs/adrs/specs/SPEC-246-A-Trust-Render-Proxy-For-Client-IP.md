# SPEC-246-A: Trust Render's Reverse Proxy for the Real Client IP

Implements **[ADR-246](../ADR-246-Trust-Render-Proxy-For-Client-IP.md)**.

## 1. Root cause

`RateLimitMiddleware._get_client_ip` and `AuditMiddleware._get_client_ip`
both read `request.client.host` directly. Behind Render's reverse proxy,
that's Render's own internal-network address (observed: `10.24.x.x`,
`10.25.x.x`, `10.26.x.x`, `10.29.x.x`) for *every* inbound request, because
uvicorn only parses `X-Forwarded-For` when the immediate TCP peer is in its
trusted list — default `127.0.0.1`, which Render's proxy peer never is.
Every real caller — browser tabs, anonymous readers, iris-mcp proxying for
every remote MCP client — therefore shares one rate-limit bucket per
category and one audit-log IP.

Separately, `_get_rate_category` routed every `/api/ai/*` path into the
10-requests-**per-hour** `anon_ai` bucket by prefix match alone, including
routes that never call an AI provider (`server-instructions`,
`providers/active`, `files/extract`, `usage`, `creation-prompts`,
`response-prompts/*`, `conversations`). `GET /api/ai/server-instructions`
in particular is fetched by iris-mcp on every session (ADR-163) and is
unauthenticated, so it alone could exhaust the global `anon_ai` bucket.

## 2. Changes

| File | Change |
|------|--------|
| `backend/app/config.py` | `AppConfig.trusted_proxy_cidrs: str`, from `IRIS_TRUSTED_PROXY_CIDRS`, default `"127.0.0.1"` (uvicorn's own default). |
| `backend/app/main.py` | New `create_asgi_app(config)`: `ProxyHeadersMiddleware(create_app(config), trusted_hosts=config.trusted_proxy_cidrs)`. `create_app` itself is unchanged. `if __name__ == "__main__"` now serves via `create_asgi_app`. |
| `backend/Dockerfile` | `CMD` now targets `app.main:create_asgi_app` instead of `app.main:create_app`. |
| `scripts/dev.sh` | `start_backend` now targets `app.main:create_asgi_app` (no-op locally at the default `trusted_proxy_cidrs`). |
| `render.yaml` | `iris-api` sets `IRIS_TRUSTED_PROXY_CIDRS=10.0.0.0/8`. |
| `backend/app/middleware/rate_limit.py` | `_get_rate_category`: `anon_ai` now requires `path.startswith("/api/ai/") and path.endswith("/ask")` (matches `/api/ai/ask` and `/api/ai/sets/{id}/ask` only), not the bare prefix. |

`create_app` deliberately stays untouched and keeps returning a plain
`FastAPI` — tests and `app/mcp_route.py`'s embedded-MCP wiring rely on
`.state` and other FastAPI/Starlette attributes a middleware-wrapped ASGI
callable doesn't expose. `create_asgi_app` is the `--factory` target used
only where traffic is actually served.

## 3. Tests (TDD)

`backend/tests/test_proxy_client_ip.py` (new; red before the `main.py` /
`config.py` change — `ImportError: cannot import name 'create_asgi_app'`
— green after):

1. `TestUntrustedProxyCollapsesCallers::test_distinct_forwarded_ips_share_one_bucket`
   — default `trusted_proxy_cidrs` (today's behaviour, unchanged): 7
   requests through a fixed non-loopback peer, each claiming a *different*
   `X-Forwarded-For`, share one bucket (limit 5) → first 5 succeed, rest
   429. Documents the bug's mechanism without needing prod config.
2. `TestTrustedProxyForwardsRealIp::test_distinct_forwarded_ips_get_independent_buckets`
   — `trusted_proxy_cidrs="10.0.0.0/8"`, same peer, same 7 distinct forwarded
   IPs → all 7 succeed (each gets its own bucket).
3. `TestTrustedProxyForwardsRealIp::test_single_abusive_forwarded_ip_still_throttled`
   — same trusted config, but all 7 requests claim the *same* forwarded IP
   → first 5 succeed, rest 429. Confirms the fix restores per-client
   limiting rather than disabling it.
4. `TestCreateAsgiApp` — `create_asgi_app` wraps in `ProxyHeadersMiddleware`
   with `trusted_hosts` sourced from config (both the configured-CIDR case
   and the untouched default).

`backend/tests/test_tokens/test_rate_limit_bucket.py` (extended; red on the
new case before the `rate_limit.py` change):

5. `test_anon_ai_bucket_covers_set_scoped_ask` — `/api/ai/sets/{id}/ask`
   still resolves to `anon_ai`.
6. `test_non_ask_ai_paths_use_anon_not_anon_ai` — `server-instructions`,
   `providers/active`, `files/extract`, `usage` resolve to `anon`, not
   `anon_ai`.

`backend/tests/test_ai/test_file_upload_router.py` — stale comment on
`test_extract_allows_anonymous` corrected (it now documents the `anon`
bucket, not `anon_ai`); no behavioural change to that test.

## 4. Verification

- **Reproduced** (pre-fix, `main` branch): local dev server, connected
  through a non-loopback peer (172.17.0.2, not 127.0.0.1 — uvicorn's default
  trusted list only covers loopback) with a distinct `X-Forwarded-For` per
  request to `GET /api/notifications/banner` (anon bucket, default limit
  30): 40 requests → 30× `200`, then `429` for the rest, despite every
  request claiming a different real-world IP.
- **Live evidence**: Render logs for `iris-api` over the last 30 days show
  the same pattern from real traffic — bursts of `429 Too Many Requests`
  from Render's internal `10.x.x.x` proxy addresses on ordinary reads
  (`/api/elements/{id}`, `/api/themes`, `/api/notifications/banner`,
  `/api/diagrams/hierarchy`), and `GET /api/ai/server-instructions` 429ing
  repeatedly since at least 2026-09-16 against the `anon_ai` bucket.
- **Fixed**: same repro, same non-loopback peer, backend started with
  `create_asgi_app` and `trusted_proxy_cidrs` covering the peer's CIDR —
  40 requests with 40 distinct `X-Forwarded-For` values → 40× `200`. A
  repeat with the *same* forwarded IP 35 times → 30× `200`, then `429`,
  confirming real abuse is still throttled.
- Full `backend/tests/` suite passes (pre-existing `tests/test_startup.py` /
  `tests/test_startup/` package name collision is unrelated to this change
  and reproduces identically on `main`).

## 5. Out of scope

- Keying `pat`/`general` buckets by authenticated identity instead of IP,
  so iris-mcp's many remote users stop sharing one bucket through the
  mcp → api hop (ADR-246 "accepting that"; needs its own ADR).
- Any Supabase-side change — none was needed; the backend never saw a
  Supabase-side error in this investigation.
