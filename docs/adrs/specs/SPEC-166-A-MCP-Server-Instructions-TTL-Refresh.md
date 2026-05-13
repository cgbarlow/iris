# SPEC-166-A: TTL background refresh for MCP server instructions

ADR: [ADR-166](../ADR-166-MCP-Server-Instructions-TTL-Refresh.md)

## Summary

Add an `asyncio` background task to the HTTP-transport lifespan that re-fetches `/api/ai/server-instructions` every `IRIS_MCP_INSTRUCTIONS_REFRESH_S` seconds (default 60) and updates `session_manager.app.instructions` if the body has changed. Preserve last-good-value on transient backend failures.

## MCP changes

### `mcp/src/iris_mcp/server_instructions.py`

Add a new helper that returns `None` instead of falling back, so the refresh loop can distinguish "real new body" from "backend unavailable":

```python
async def try_fetch_server_instructions(iris_url: str) -> str | None:
    """Like `fetch_server_instructions` but returns None on any failure
    instead of the hardcoded fallback. Use in the refresh loop where
    we want to preserve the previously-fetched body if the backend is
    transiently unavailable; the initial startup fetch still uses
    `fetch_server_instructions` so the very first request never sees
    `instructions=None`.
    """
    try:
        async with httpx.AsyncClient(base_url=iris_url, timeout=5.0) as c:
            response = await c.get("/api/ai/server-instructions")
            response.raise_for_status()
            payload = response.json()
            body = payload.get("body") if isinstance(payload, dict) else None
            if isinstance(body, str) and body.strip():
                return body
            return None
    except (httpx.HTTPError, ValueError):
        return None
```

The existing `fetch_server_instructions` is kept unchanged for the startup-fetch path (where the hardcoded fallback is the right answer to avoid `None` on the first request).

### `mcp/src/iris_mcp/http_main.py`

Update the lifespan:

```python
import asyncio

REFRESH_DEFAULT_S = 60.0

def create_app() -> FastAPI:
    iris_url = os.environ.get("IRIS_API_URL")
    if not iris_url:
        raise RuntimeError(...)

    session_manager = build_session_manager()

    refresh_interval = float(
        os.environ.get("IRIS_MCP_INSTRUCTIONS_REFRESH_S", REFRESH_DEFAULT_S),
    )

    async def _refresh_loop() -> None:
        # Periodic background refresh. Preserves last-good on transient
        # backend failures (try_fetch returns None instead of fallback).
        while True:
            await asyncio.sleep(refresh_interval)
            fresh = await try_fetch_server_instructions(iris_url)
            if fresh is not None and fresh != session_manager.app.instructions:
                session_manager.app.instructions = fresh
                logger.info("iris-mcp: refreshed server instructions body")

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        # Initial blocking fetch — never let the first request see None.
        session_manager.app.instructions = await fetch_server_instructions(
            iris_url,
        )

        refresh_task: asyncio.Task[None] | None = None
        if refresh_interval > 0:
            refresh_task = asyncio.create_task(_refresh_loop())

        try:
            async with session_manager.run():
                yield
        finally:
            if refresh_task is not None:
                refresh_task.cancel()
                try:
                    await refresh_task
                except asyncio.CancelledError:
                    pass

    app = FastAPI(..., lifespan=lifespan)
    app.state.session_manager = session_manager
    ...
```

`IRIS_MCP_INSTRUCTIONS_REFRESH_S=0` disables the loop entirely (useful for deterministic tests).

## Tests

### `mcp/tests/test_server_instructions.py`

Add a `TestTryFetchServerInstructions` class mirroring `TestFetchServerInstructions` but asserting `None` on failure modes instead of the fallback constant:

- Happy path returns body.
- Empty body → None.
- Whitespace body → None.
- 500 → None.
- 404 → None.
- Network error → None.
- Malformed JSON → None.

### `mcp/tests/test_http_main.py`

Add a `TestRefreshLoop` class:

```python
class TestRefreshLoop:
    def test_lifespan_picks_up_updated_body(
        self, monkeypatch, respx_mock,
    ) -> None:
        """Refresh loop updates `instructions` when the backend body
        changes."""
        monkeypatch.setenv("IRIS_API_URL", "http://iris.test")
        monkeypatch.setenv("IRIS_MCP_INSTRUCTIONS_REFRESH_S", "0.05")
        route = respx_mock.get(
            "http://iris.test/api/ai/server-instructions",
        )
        # First call returns the boot body, subsequent calls return the
        # updated body — simulating an admin edit landing mid-session.
        route.mock(side_effect=[
            httpx.Response(200, json={"body": "BOOT BODY"}),
            httpx.Response(200, json={"body": "ADMIN-EDITED BODY"}),
            httpx.Response(200, json={"body": "ADMIN-EDITED BODY"}),
        ])
        from iris_mcp.http_main import create_app

        app = create_app()
        with TestClient(app):
            sm = app.state.session_manager
            # Initial fetch happens in lifespan startup.
            assert sm.app.instructions == "BOOT BODY"
            # Wait long enough for one refresh tick.
            for _ in range(20):
                time.sleep(0.05)
                if sm.app.instructions == "ADMIN-EDITED BODY":
                    break
            assert sm.app.instructions == "ADMIN-EDITED BODY"

    def test_lifespan_preserves_body_on_transient_failure(
        self, monkeypatch, respx_mock,
    ) -> None:
        """When the backend fails mid-loop, the previously-fetched body
        is preserved rather than overwritten with the fallback."""
        monkeypatch.setenv("IRIS_API_URL", "http://iris.test")
        monkeypatch.setenv("IRIS_MCP_INSTRUCTIONS_REFRESH_S", "0.05")
        respx_mock.get(
            "http://iris.test/api/ai/server-instructions",
        ).mock(side_effect=[
            httpx.Response(200, json={"body": "GOOD BODY"}),
            httpx.ConnectError("backend down"),
            httpx.ConnectError("backend still down"),
        ])
        from iris_mcp.http_main import create_app

        app = create_app()
        with TestClient(app):
            sm = app.state.session_manager
            assert sm.app.instructions == "GOOD BODY"
            # Wait long enough for at least one failed refresh tick.
            time.sleep(0.2)
            # The good body is still there — the failed refreshes didn't
            # clobber it with the fallback.
            assert sm.app.instructions == "GOOD BODY"

    def test_refresh_disabled_when_interval_zero(
        self, monkeypatch, respx_mock,
    ) -> None:
        """Setting IRIS_MCP_INSTRUCTIONS_REFRESH_S=0 disables the loop —
        only the initial startup fetch runs."""
        monkeypatch.setenv("IRIS_API_URL", "http://iris.test")
        monkeypatch.setenv("IRIS_MCP_INSTRUCTIONS_REFRESH_S", "0")
        route = respx_mock.get(
            "http://iris.test/api/ai/server-instructions",
        ).mock(
            return_value=httpx.Response(200, json={"body": "ONCE"}),
        )
        from iris_mcp.http_main import create_app

        app = create_app()
        with TestClient(app):
            time.sleep(0.2)
            sm = app.state.session_manager
            assert sm.app.instructions == "ONCE"
            # Only the lifespan startup fetch ran.
            assert route.call_count == 1
```

## Versioning

`mcp/pyproject.toml`: 6.0.4 → 6.0.5. Patch bump — operator-experience fix, no public API change.
`frontend/package.json`: matched 6.0.5.

## CHANGELOG

Add a `[6.0.5]` entry documenting the TTL refresh, the new env var, and the issue #119 closing context (this is the last gap that prevented admin edits from reaching claude.ai in real time).

## Acceptance criteria

- [ ] `try_fetch_server_instructions` returns body on success, `None` on every failure path that `fetch_server_instructions` falls back from.
- [ ] iris-mcp lifespan startup still does an immediate blocking fetch — no regression on the v6.0.4 wiring.
- [ ] Refresh loop picks up an admin edit within `IRIS_MCP_INSTRUCTIONS_REFRESH_S` seconds.
- [ ] Refresh loop preserves last-good body when the backend fails transiently.
- [ ] Setting `IRIS_MCP_INSTRUCTIONS_REFRESH_S=0` disables the loop.
- [ ] Cancellation on lifespan shutdown is clean (no hung tasks, no leaked exceptions).
- [ ] All v6.0.4 regression tests still pass.
- [ ] Manual smoke after deploy: admin edits the `mcp_server_instructions` body, waits ≤ 60 s, fresh claude.ai chat sees the new body in `InitializeResult` without a Render redeploy.
