# ADR-134: iris-mcp as a Standalone Service

Status: Accepted (2026-05-04)

## Context

[ADR-133](ADR-133-MCP-Remote-Transport.md) decided to mount the
Streamable-HTTP MCP server **on the iris backend** at `/mcp`. The
stated reasoning was solid: shared hostname, shared TLS, shared
rate-limit middleware, shared audit log, no extra infrastructure to
host. We shipped it and it worked end-to-end.

In production on Render's free dyno (512 MB RAM), it didn't survive
contact with traffic. Every embedded /mcp request:

1. Loads the `mcp` SDK module graph (~30 MB resident).
2. Holds a long-lived `StreamableHTTPSessionManager` task group via
   the FastAPI lifespan.
3. Round-trips through `httpx.ASGITransport(app=app)` — the in-process
   call lands the request on the same FastAPI app's middleware stack
   *again*, doubling the working memory of an MCP-driven request.

Combined with the iris backend's existing footprint (cairosvg,
python-pptx, pdfplumber, asyncpg, scenia adapter, etc.), the dyno
went over 512 MB and Render OOM-killed the process mid-stream. Users
saw `Couldn't reach the MCP server` in Claude Desktop.

## Decision

**Run iris-mcp as a separate Render web service** that talks to the
iris backend over normal HTTP via a configured `IRIS_API_URL`. The
backend stays at its old footprint; iris-mcp gets its own 512 MB
dyno (sufficient for a process that does almost nothing but proxy
JSON-RPC).

The embedded mount from ADR-133 (`backend/app/mcp_route.py`) stays
in the codebase **but is opt-in via `IRIS_EMBEDDED_MCP=1`** — useful
for local dev (one process, one terminal) and for deployments where
memory pressure isn't a concern. Defaults off in production.

## Why not just upgrade the Render plan

A $7/mo Render Starter plan would solve the OOM. Two reasons not to
make that the answer:

- It pushes a dependency-injection problem onto a paid tier: anyone
  self-hosting iris on the equivalent free tier elsewhere (Fly.io
  free, Railway hobby, a small Hetzner box) hits the same wall. The
  fix should work on the same hardware that runs the backend today.
- The MCP service is genuinely better as a separate process. It
  scales independently (an agent storm doesn't slow down the web
  frontend's API), it can be restarted without touching the API, and
  its logs are isolated for the hot-debug-while-an-agent-is-stuck
  case that we'll inevitably hit.

## Why not just embed but make it lighter

We could trim the backend's heavy deps (cairosvg, python-pptx, etc.)
to claw back memory. But:

- Those deps exist for real features (thumbnail rendering, PowerPoint
  import). Lazy-importing them helps, but only postpones the
  collision the next time the backend grows.
- The embedded MCP path's *intrinsic* cost — loading the MCP SDK plus
  the `httpx.ASGITransport` round-trip — doesn't shrink. It's
  structural.
- Splitting cleanly removes the loop entirely.

## Why not WebSockets

Same answer as ADR-133: Streamable HTTP is what Claude Desktop's
remote-MCP UI accepts. Adding WebSockets is in scope only if a client
that requires it shows up.

## Auth & rate-limit consequences

Auth is unchanged in spirit — the standalone service extracts the
Bearer token from the incoming request and forwards it on the
outbound `IrisClient` calls. The rate-limit bucket attribution
*shifts* to the iris backend's middleware as it sees the *outbound*
calls — same buckets (`pat`, `anon`, `anon_ai`), same accounting, no
double-counting from the in-process round-trip we used to do.

There is one new failure mode: if the iris backend is down,
iris-mcp's tool calls fail. That's correct: there's nothing useful
the MCP server can do without the backend behind it. The error
mapping in `iris_mcp.errors` already handles 5xx / connection
failures gracefully.

## Compatibility

- The stdio transport (ADR-131) is untouched — `iris_mcp.__main__`
  still works exactly as documented.
- The embedded mount (ADR-133) is preserved as an opt-in for
  developers and self-hosters who don't want the second service.
  Default is off.
- The MCP URL changes for end users — they paste the standalone
  service's URL into Claude Desktop, not the iris backend's. Docs
  updated.

## Out of scope (deferred)

- Per-tool per-user RBAC beyond what the iris backend already
  enforces. Same as ADR-133.
- A shared docker-compose for self-hosters who want all three
  services (backend, frontend, mcp) up locally. Useful but out of
  scope for this change.

## See also

- [ADR-131](ADR-131-MCP-Server-Architecture.md) — stdio transport.
- [ADR-133](ADR-133-MCP-Remote-Transport.md) — original embedded-
  mount decision. Not superseded — embedded mount stays as opt-in;
  this ADR makes the *deployment topology* the standalone service.
- SPEC-134-A — implementation contract.
