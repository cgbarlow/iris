# ADR-165: Surface MCP server `instructions` over the HTTP transport

Status: Accepted (2026-05-13)
Extends: [ADR-163](ADR-163-Centralised-MCP-Server-Instructions.md), [ADR-164](ADR-164-OAuth-2.1-for-MCP.md), [ADR-134](ADR-134-Standalone-MCP-HTTP-Service.md)

## Context

ADR-163 (v5.18.0) lifted the universal ORIENT-FIRST protocol out of every per-scope `mcp_system_context` into a server-wide channel — the MCP SDK's `Server(instructions=...)` field, returned in the `InitializeResult` to every connected MCP client. iris-mcp fetches the admin-editable body from the backend at startup and passes it to `build_server(client, instructions=...)`.

The ADR-163 wiring landed in **`mcp/src/iris_mcp/__main__.py`** — the **stdio** entry point. It was not applied to **`mcp/src/iris_mcp/asgi.py:build_session_manager()`** — the **HTTP** entry point used by the standalone Render service (ADR-134) and consumed by claude.ai over OAuth (ADR-164).

Concretely:

```python
# asgi.py:90
server = build_server(_LazyClient())   # no instructions= kwarg → instructions=None
```

Effect: every HTTP MCP client (claude.ai web app, Claude Desktop's "Add custom connector", any future hosted-MCP client) connects to iris-mcp and receives an `InitializeResult` with **no `instructions` body**. The ORIENT-FIRST protocol — the imperative "INVOKE the structural-overview call... NOT as a follow-up 'want me to load it?' prompt" — never reaches the model.

Issue [#119](https://github.com/cgbarlow/iris/issues/119) reports the user-visible regression: opening the Outcomes Theory Book in claude.ai shows the per-scope menu as plain text and asks the user *"Want me to load the package hierarchy?"* instead of auto-loading it and offering an `AskUserQuestion` widget. The 5.x behaviour worked because the orient protocol was embedded inline in `mcp_system_context` back then; v5.18.0's separation broke the HTTP path only.

Prior fixes for the same issue (v6.0.1 m055, v6.0.2 m056, v6.0.3) targeted a related but distinct bug — the `iris_package_hierarchy` → `package_hierarchy` tool-name substitution. That path is fixed; the live `mcp_system_context` carries the correct name. But the imperative wrapper that says *"don't ask, just call it"* is still never delivered.

The gap was uncovered because the v5.18.0 wiring test (`test_server_instructions_wiring.py`) only exercises `build_server()` in isolation; there is no test verifying that the **HTTP transport** end-to-end advertises the instructions on `InitializeResult`. The stdio path had the same test gap but the wiring happened to be correct there.

## Decision

Plumb `instructions=` through the HTTP transport so it matches the stdio behaviour.

1. **`mcp/src/iris_mcp/asgi.py:build_session_manager()`** gains an `instructions: str | None = None` keyword argument and forwards it to `build_server(_LazyClient(), instructions=instructions)`. Default `None` keeps the function signature non-breaking for any external caller and matches `build_server()`'s own default.

2. **`mcp/src/iris_mcp/http_main.py:create_app()`** calls `await fetch_server_instructions(iris_url)` once at app-construction time (inside an async helper invoked from the FastAPI lifespan startup) and passes the result to `build_session_manager(instructions=...)`. Same fallback semantics as stdio: if the backend is unreachable or returns an empty body, the hardcoded `_FALLBACK_INSTRUCTIONS` baseline ships.

3. **Tests** — add three regression tests:
   - `test_http_main.py`: `create_app()` builds an app whose session manager's wrapped server has `instructions` set to the value returned by `fetch_server_instructions` (mocked).
   - `test_http_main.py`: when `fetch_server_instructions` falls back (mock the HTTP call to error), the server still has the fallback body — never `None`.
   - `test_server_instructions_wiring.py`: `build_session_manager(instructions=...)` round-trips the value to the underlying server.

Pin the contract: every transport iris-mcp ships must advertise `instructions`. No HTTP-vs-stdio drift.

## Why fetch once at app construction (not per-request)

- The `instructions` body is a singleton; admin edits via `/admin/settings/ai` are infrequent (typically once at deploy time, occasionally during prompt-engineering iteration).
- claude.ai's MCP client caches `InitializeResult` for the session lifetime. Per-request fetches would not propagate edits any faster.
- Fetch-on-startup matches the stdio model and keeps the request hot path free of backend round-trips.
- Operationally consistent: admin updates the singleton → restarts iris-mcp → next session sees the new body. Documented in ADR-163.

## Why not move the fetch into `build_session_manager()`

- `build_session_manager()` is called from a sync context (`create_app()` returns a configured `FastAPI`); blocking on an async fetch there would require an `asyncio.run()` inside a function that may itself be called from inside an event loop in test fixtures.
- Keeping the fetch in `create_app()` (which has an async lifespan available) preserves a clean separation: `build_session_manager` is pure wiring, `create_app` owns I/O.

## Consequences

- One added kwarg on `build_session_manager()`. Backwards-compatible default.
- One added `await fetch_server_instructions(...)` call in `create_app()`. App startup gains one backend round-trip with a 5 s timeout and graceful fallback (already implemented in `server_instructions.py`).
- Three new regression tests covering the HTTP path.
- claude.ai users opening any authored scope now see the ORIENT-FIRST protocol in effect: TOC auto-loaded, menu via `AskUserQuestion` widget, no "want me to load it?" preamble.
- Version bump v6.0.3 → v6.0.4. Patch-level (bug fix, no API surface change).

## See also

- [ADR-163](ADR-163-Centralised-MCP-Server-Instructions.md) — the original lift of orient-first to server-wide `instructions`.
- [ADR-134](ADR-134-Standalone-MCP-HTTP-Service.md) — why iris-mcp ships as a separate HTTP service.
- [ADR-164](ADR-164-OAuth-2.1-for-MCP.md) — the HTTP transport claude.ai uses to connect.
- [SPEC-165-A](specs/SPEC-165-A-MCP-Server-Instructions-Over-HTTP-Transport.md) — wiring details and test plan.
- Issue [#119](https://github.com/cgbarlow/iris/issues/119) — the regression report.
