# ADR-246: Trust Render's Reverse Proxy for the Real Client IP

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-246 |
| **Initiative** | Stop false-positive rate limiting reported as "Supabase is rate limiting us" after the Supabase project moved to the free tier |
| **Proposed By** | Engineering |
| **Date** | 2026-09-23 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** `RateLimitMiddleware` (`app/middleware/rate_limit.py`,
SPEC-005-B) and `AuditMiddleware` (`app/middleware/audit.py`), both of which
key their per-client state on `request.client.host`, and the `iris-api` /
`iris-mcp` Render web services, which sit behind Render's reverse proxy —
every inbound connection to the container originates from Render's own
internal network, not the caller's real IP,

**facing** the report that Iris "gets rate limited" after the Supabase
project moved to the free tier, which we traced (not to Supabase — the
backend never saw a Supabase-side 429 or connection error) but to our own
`429 Too Many Requests`, confirmed both locally (reproduced by connecting to
the dev server through a non-loopback peer address with a distinct
`X-Forwarded-For` per request: 30 simulated distinct callers collapsed into
one bucket, tripping at #31) and in the live Render logs for `iris-api`
(`10.29.140.12`, `10.29.109.72`, `10.25.50.133`, … — Render's internal
proxy addresses — repeatedly hitting 429 together on ordinary reads, and
`GET /api/ai/server-instructions`, a zero-cost DB lookup iris-mcp calls
every session (ADR-163), 429ing against the 10/hour `anon_ai` bucket since
at least 2026-09-16); root cause is that uvicorn's default trusted-proxy
list is `127.0.0.1` only, so `X-Forwarded-For` from Render's proxy is
ignored and `request.client.host` is Render's own address for every
request — collapsing every real visitor, browser tab, and iris-mcp-proxied
MCP caller into one shared rate-limit identity (and one shared audit-log
IP),

**we decided to** add `app.main.create_asgi_app` — the actual `--factory`
target used to serve traffic (`create_app` itself is unchanged and keeps
returning a plain `FastAPI` for tests and the embedded-MCP mount) — which
wraps the FastAPI app in uvicorn's `ProxyHeadersMiddleware`, trusting
`X-Forwarded-For` only from `config.trusted_proxy_cidrs`
(`IRIS_TRUSTED_PROXY_CIDRS`, defaulting to uvicorn's own default of
`127.0.0.1` so self-hosted/dev deployments are unaffected unless they opt
in). Render's `iris-api` service now sets `IRIS_TRUSTED_PROXY_CIDRS=
10.0.0.0/8` (`render.yaml`), matching the internal proxy addresses observed
in its logs. Separately, `_get_rate_category` no longer routes every
`/api/ai/*` path into the 10/hour `anon_ai` bucket by prefix alone — only
`/api/ai/ask` and `/api/ai/sets/{id}/ask`, the two routes that actually
spend AI-provider tokens, do; the other `/api/ai/*` reads (`server-
instructions`, `providers/active`, `files/extract`, `usage`, …) fall into
the much larger `anon` bucket like any other anonymous read,

**and neglected** (1) raising the `anon`/`anon_ai` limits instead — rejected
as treating the symptom: the buckets were sized assuming one bucket per
real caller, which trusting the proxy restores, so raising limits would
just make the still-broken global sharing less noticeable rather than
fixing it; (2) setting `--proxy-headers --forwarded-allow-ips` as uvicorn
CLI flags on the Docker `CMD` — rejected: it isn't testable, it's easy to
forget on a future deployment change, and it would apply unconditionally to
*any* deployment of this image (not just Render) since it can't read
per-environment config; the config-driven `trusted_proxy_cidrs` field
achieves the same result and is covered by `tests/test_proxy_client_ip.py`;
(3) keying rate limits on authenticated identity (PAT/user id) instead of
IP — a real, complementary improvement (iris-mcp is itself a shared proxy,
so even a correctly-forwarded client IP is iris-mcp's own outbound address
for every remote MCP user), but a larger design change; tracked as a
follow-up, not required to fix the reported symptom,

**to achieve** rate-limit and audit-log buckets that reflect real distinct
callers again, eliminating the false-positive 429s without weakening actual
per-client abuse protection (verified: a single IP hammering the endpoint
through the trusted proxy still throttles correctly) and without any
Supabase-side or performance change,

**accepting that** iris-mcp's own traffic to `iris-api` will still share one
bucket across all of iris-mcp's remote users for the `anon`/`anon_ai`/`pat`
categories, since IP-based limiting can't distinguish end users behind a
single proxying service — the follow-up in "neglected" (3) is needed to
close that gap fully.

---

## Consequences

- No schema, endpoint, MCP tool, or CLI change; surface parity (§14) and
  migration parity (§15) are N/A.
- `AuditMiddleware`'s recorded IP is corrected as a side effect of the same
  fix (it reads `request.client.host` too) — no separate code change needed.
- Self-hosted/SQLite deployments are unaffected unless they set
  `IRIS_TRUSTED_PROXY_CIDRS` themselves (default stays `127.0.0.1`).
- Follow-up (tracked, not part of this ADR): key `pat`/`general` buckets by
  authenticated identity rather than IP, so iris-mcp's many remote users
  stop sharing one bucket through the mcp → api hop.

## Dependencies

- ADR-123 (Anonymous Read-Only Bypass — origin of the `anon`/`anon_ai`
  buckets this ADR corrects the keying and categorisation for).
- ADR-129 (Public HTTP API Stabilisation — origin of the `anon` bucket
  split from `general`).
- ADR-134 (standalone iris-mcp service — the proxy hop whose traffic this
  ADR's accepted trade-off still leaves bucketed together).
- ADR-163 (MCP server instructions — the endpoint whose mis-bucketing this
  ADR fixes).

## References

- Implementation spec: [SPEC-246-A](./specs/SPEC-246-A-Trust-Render-Proxy-For-Client-IP.md)
