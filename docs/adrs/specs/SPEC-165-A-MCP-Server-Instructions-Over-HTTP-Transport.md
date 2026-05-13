# SPEC-165-A: Surface MCP server `instructions` over the HTTP transport

ADR: [ADR-165](../ADR-165-MCP-Server-Instructions-Over-HTTP-Transport.md)

## Summary

Plumb the `instructions` body fetched from the backend through the HTTP transport entry point so it reaches every claude.ai / Claude Desktop / hosted-MCP client. The wiring already exists for stdio (ADR-163); this spec mirrors it for HTTP.

## MCP changes

### `mcp/src/iris_mcp/asgi.py`

`build_session_manager()` accepts a new keyword-only `instructions` parameter and forwards it to `build_server`:

```python
def build_session_manager(
    *,
    instructions: str | None = None,
) -> StreamableHTTPSessionManager:
    """Build a stateless Streamable HTTP session manager.

    `instructions` (ADR-165): forwarded to `build_server(...)` and
    exposed on the MCP `InitializeResult.instructions` field returned
    to every connected client. None disables the field.
    """
    server = build_server(_LazyClient(), instructions=instructions)
    return StreamableHTTPSessionManager(
        app=server, stateless=True, json_response=True,
    )
```

Default `None` keeps backwards compatibility for any external test or harness that calls `build_session_manager()` directly.

### `mcp/src/iris_mcp/http_main.py`

`create_app()` builds the session manager up front with no instructions, then fetches the body in the lifespan startup and mutates `session_manager.app.instructions` before the first request arrives:

```python
from iris_mcp.server_instructions import fetch_server_instructions

def create_app() -> FastAPI:
    iris_url = os.environ.get("IRIS_API_URL")
    if not iris_url:
        raise RuntimeError(...)

    session_manager = build_session_manager()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        # ADR-165 (v6.0.4): mirror stdio wiring (ADR-163). The MCP SDK
        # reads Server.instructions per request when constructing the
        # InitializeResult, so post-construct mutation is safe.
        session_manager.app.instructions = await fetch_server_instructions(
            iris_url,
        )
        async with session_manager.run():
            yield

    app = FastAPI(..., lifespan=lifespan)
    app.state.session_manager = session_manager   # for regression test introspection
    ...
```

The fetch lives in the lifespan rather than directly in `create_app` for two reasons:

1. `create_app` must remain sync-callable from any context. Async test cases (e.g. `test_oauth_resource.py::TestHttpMainEndpointMounted` and any future asgi-transport test) build the app from inside a running event loop; `asyncio.run()` inside `create_app` would raise `RuntimeError: asyncio.run() cannot be called from a running event loop`.
2. uvicorn's lifespan protocol is the canonical place for startup I/O. The pattern matches how every other framework component (`StreamableHTTPSessionManager.run()`) is already wired here.

Fallback semantics are inherited from `fetch_server_instructions`: any network error, HTTP error, malformed JSON, or empty body yields `_FALLBACK_INSTRUCTIONS` instead of raising or returning `None`. The HTTP transport therefore **never** advertises `instructions=None` in production — the worst case is the frozen baseline.

## Tests

### `mcp/tests/test_server_instructions_wiring.py`

Add a class verifying `build_session_manager` forwards `instructions`:

```python
class TestBuildSessionManagerInstructionsWiring:
    def test_instructions_passed_through(self) -> None:
        sm = build_session_manager(instructions="HTTP HELLO")
        assert sm.app.instructions == "HTTP HELLO"   # underlying server

    def test_no_instructions_kwarg_yields_none(self) -> None:
        sm = build_session_manager()
        assert sm.app.instructions is None
```

The `StreamableHTTPSessionManager`'s `app` is the wrapped `Server`; `server.instructions` is the SDK-exposed attribute already used in the existing build-server wiring tests.

### `mcp/tests/test_http_main.py`

Add three tests covering the lifespan fetch + fallback paths. Each enters the lifespan via `TestClient(app)`'s context manager to trigger startup:

```python
class TestCreateAppFetchesInstructions:
    def test_lifespan_fetches_and_wires_instructions(
        self, respx_mock, monkeypatch,
    ) -> None:
        monkeypatch.setenv("IRIS_API_URL", "http://iris.test")
        respx_mock.get("http://iris.test/api/ai/server-instructions").mock(
            return_value=httpx.Response(200, json={"body": "ORIENT BODY"}),
        )
        app = create_app()
        with TestClient(app):                     # triggers lifespan startup
            sm = app.state.session_manager
            assert sm.app.instructions == "ORIENT BODY"

    def test_lifespan_falls_back_when_backend_unreachable(
        self, respx_mock, monkeypatch,
    ) -> None:
        monkeypatch.setenv("IRIS_API_URL", "http://iris.test")
        respx_mock.get("http://iris.test/api/ai/server-instructions").mock(
            side_effect=httpx.ConnectError("nope"),
        )
        app = create_app()
        with TestClient(app):
            sm = app.state.session_manager
            assert sm.app.instructions is not None  # fallback baseline
            assert "ORIENT-FIRST PROTOCOL" in sm.app.instructions

    def test_lifespan_falls_back_on_http_error(
        self, respx_mock, monkeypatch,
    ) -> None:
        monkeypatch.setenv("IRIS_API_URL", "http://iris.test")
        respx_mock.get("http://iris.test/api/ai/server-instructions").mock(
            return_value=httpx.Response(500, json={"detail": "boom"}),
        )
        app = create_app()
        with TestClient(app):
            sm = app.state.session_manager
            assert sm.app.instructions == _FALLBACK_INSTRUCTIONS
```

The `app_with_backend` fixture also gains a respx mock for `/api/ai/server-instructions` so unrelated tests (`/info`, favicon, root-mount) don't trigger a real network call during lifespan startup. The mock body for that fixture is arbitrary — those tests don't inspect `instructions`.

### Existing tests preserved

All three existing `TestBuildServerInstructionsWiring` cases stay green — they exercise `build_server` directly with no transport involvement. Pinning them in place guards against accidental regressions on the stdio path.

## Versioning

`mcp/pyproject.toml`: 6.0.3 → 6.0.4. Patch bump — wiring fix, no public API change. `frontend/package.json` follows the same v6.0.4 tag for release-tracking consistency with v6.0.x.

## CHANGELOG

```markdown
## [6.0.4] - 2026-05-13

### Fixed

- **MCP orient-first protocol over HTTP transport (issue #119, ADR-165).** v5.18.0 (ADR-163) lifted the universal ORIENT-FIRST protocol into the MCP `Server(instructions=...)` channel and wired it for stdio. The parallel wiring for the HTTP transport (`asgi.py:build_session_manager`, `http_main.py:create_app`) was missed, so every claude.ai connection received `InitializeResult` with no `instructions` body. Model couldn't see the "INVOKE the structural-overview call... NOT as a follow-up 'want me to load it?' prompt" directive, so opening a scope produced a paraphrased text menu instead of the auto-loaded TOC + `AskUserQuestion` flow. Fix plumbs `instructions=` through `build_session_manager(instructions=...)` and fetches the body once at `create_app()`. Regression test `test_http_main.py::TestCreateAppFetchesInstructions` pins the wiring end-to-end.
```

## Acceptance criteria

- [ ] `build_session_manager(instructions="X")` produces a session manager whose wrapped server has `instructions == "X"`.
- [ ] `build_session_manager()` (no kwarg) produces a session manager whose wrapped server has `instructions is None` (backwards-compatible default).
- [ ] `create_app()` fetches `/api/ai/server-instructions` from `IRIS_API_URL` and attaches the body to the session manager.
- [ ] When the backend is unreachable, `create_app()` still produces a session manager with the fallback `instructions` body — never `None`.
- [ ] Existing stdio wiring (`__main__.py`) is unchanged.
- [ ] All existing `mcp/tests/` cases pass; three new regression tests pass.
- [ ] Manual smoke-test: claude.ai connects to UAT iris-mcp via OAuth, opens the Outcomes Theory Book, sees the TOC auto-loaded and the four-option menu via `AskUserQuestion` widget (matching `5.x.previous.txt`).
