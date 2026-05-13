# ADR-166: TTL background refresh for MCP server instructions

Status: Accepted (2026-05-13)
Extends: [ADR-163](ADR-163-Centralised-MCP-Server-Instructions.md), [ADR-165](ADR-165-MCP-Server-Instructions-Over-HTTP-Transport.md)

## Context

ADR-163 made the MCP `Server.instructions` body admin-editable from `/admin/settings/ai`. ADR-165 wired that body through the HTTP transport so claude.ai actually receives it. Issue #119 testing surfaced a third gap: **admin edits don't take effect until the iris-mcp service is manually redeployed.**

The iris-mcp HTTP service fetches the body once in its FastAPI lifespan startup hook (`http_main.py:create_app`). After that, the fetched value is held in `session_manager.app.instructions` for the lifetime of the process. Subsequent admin edits to the `/api/ai/server-instructions` row do update the backend response immediately, but iris-mcp keeps serving its stale copy until Render restarts the container.

Observed during issue #119 debugging:

1. Admin paste the canonical strong-wording body into `/admin/settings/ai`.
2. `curl /api/ai/server-instructions` confirms the new body is live on iris-api.
3. `curl iris-mcp.../` (MCP `initialize`) still returns the **old weak body** that iris-mcp cached at boot.
4. claude.ai keeps following the weak body until Render redeploys iris-mcp.

That breaks the "admin-editable" promise of ADR-163. Every iteration of prompt-engineering on the orient protocol currently requires a manual Render redeploy.

## Decision

Add a TTL background-refresh loop to the HTTP-transport lifespan.

- The lifespan startup hook still does the initial blocking fetch (so the very first request never sees `instructions=None`).
- After that, an `asyncio` background task re-fetches `/api/ai/server-instructions` every `IRIS_MCP_INSTRUCTIONS_REFRESH_S` seconds (default **60**) and mutates `session_manager.app.instructions` if the new body differs from the current one.
- If the backend is transiently unavailable mid-loop, **keep the last good value** rather than overwriting with the fallback baseline. Avoids "admin body briefly disappears during a backend hiccup". A new helper `try_fetch_server_instructions(iris_url) -> str | None` returns `None` on any failure (network, HTTP, malformed body, empty body); the loop only writes if the result is `not None` and `!= current`.
- On lifespan shutdown, cancel the background task and swallow `CancelledError` cleanly.
- Refresh interval is **configurable** via `IRIS_MCP_INSTRUCTIONS_REFRESH_S`. Set to `0` to disable refresh entirely (e.g. for tests; the lifespan still does the initial fetch). Set to a small value for prompt-engineering iteration.

The MCP SDK reads `Server.instructions` per request when constructing `InitializeResult`, so post-startup mutation is observed by every new claude.ai session without per-request fetch overhead.

## Why TTL (not per-init fetch)

- Per-init fetch couples MCP-init latency to backend availability and adds a backend round-trip on every claude.ai session start. With claude.ai's stateless-mode connections (ADR-134, `stateless=True`), that's potentially every conversation turn — far more pressure than admin edit cadence justifies.
- A 60-second TTL means admin edits propagate to claude.ai within a minute. The orient protocol is not a hot-iteration knob; minute-scale propagation matches the workflow.
- Per-init fetch would also need to deal with the "backend unavailable on init" case identically to lifespan startup (keep advertising last good value), so the implementation overhead isn't materially smaller.

## Why an env-var-tunable interval

- The default 60 s is a guess at "fast enough for prompt-engineering, slow enough to not hammer the backend". Self-hosters with different cadences (e.g. long-stable production deployment vs. active development) should be able to tune without rebuilding.
- `0` disables refresh — useful in tests that want deterministic instructions (the test injects whatever body it wants via `respx_mock` once, doesn't want the loop racing the assertion).

## Why mutate `session_manager.app.instructions` directly

- The MCP SDK exposes `instructions` as a public `__init__` attribute, read per request. Mutation is supported by the contract.
- Wrapping the Server to add a callable `instructions_provider()` hook would be cleaner architecturally but is much more code for a single concern. The session manager's `app` is already the Server instance; one attribute write is the simplest path.

## Consequences

- One new helper `try_fetch_server_instructions(iris_url) -> str | None` in `server_instructions.py`.
- `http_main.py` lifespan gains a background task with start + cancel-on-shutdown.
- New env var `IRIS_MCP_INSTRUCTIONS_REFRESH_S` (default 60, set 0 to disable).
- Render `render.yaml` left unchanged — default 60s applies via the implicit default.
- 4 new regression tests:
  - `try_fetch_server_instructions` returns the body on success.
  - `try_fetch_server_instructions` returns `None` on every failure mode that `fetch_server_instructions` falls back from.
  - The lifespan refresh loop picks up an updated body within the TTL window.
  - The lifespan refresh loop preserves the last good body when the backend transiently fails.
- Documentation update — `docs/prompts/mcp-server-instructions.md` "Why this works" section gains a note about minute-scale propagation.
- Version bump v6.0.4 → v6.0.5. Patch-level (operator-experience fix, no API surface change).

## See also

- [ADR-163](ADR-163-Centralised-MCP-Server-Instructions.md) — original admin-editable instructions design.
- [ADR-165](ADR-165-MCP-Server-Instructions-Over-HTTP-Transport.md) — wiring fix that made the issue visible.
- [SPEC-166-A](specs/SPEC-166-A-MCP-Server-Instructions-TTL-Refresh.md) — implementation details.
- Issue [#119](https://github.com/cgbarlow/iris/issues/119) — original regression report.
