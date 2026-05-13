"""Tests for the standalone iris-mcp HTTP service (SPEC-134-A,
SPEC-165-A, SPEC-166-A)."""

from __future__ import annotations

import time
from collections.abc import Iterator

import httpx
import pytest
import respx
from fastapi.testclient import TestClient


@pytest.fixture
def app_with_backend(
    monkeypatch: pytest.MonkeyPatch,
    respx_mock: respx.Router,
) -> Iterator[TestClient]:
    # ADR-165 (v6.0.4): create_app() now fetches /api/ai/server-instructions
    # at startup. Mock it so non-instruction tests don't depend on an
    # unreachable backend (fall through is benign but slows the suite).
    # ADR-166 (v6.0.5): disable the refresh loop for unrelated tests so
    # the background task doesn't race other assertions.
    monkeypatch.setenv("IRIS_API_URL", "http://iris-backend.test")
    monkeypatch.setenv("IRIS_MCP_INSTRUCTIONS_REFRESH_S", "0")
    respx_mock.get(
        "http://iris-backend.test/api/ai/server-instructions",
    ).mock(
        return_value=httpx.Response(200, json={"body": "TEST INSTRUCTIONS"}),
    )
    from iris_mcp.http_main import create_app

    app = create_app()
    with TestClient(app) as client:
        yield client


class TestCreateApp:
    def test_refuses_to_start_without_iris_api_url(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("IRIS_API_URL", raising=False)
        from iris_mcp.http_main import create_app

        with pytest.raises(RuntimeError, match="IRIS_API_URL"):
            create_app()


class TestInfoRoute:
    def test_info_returns_service_identity(
        self, app_with_backend: TestClient,
    ) -> None:
        # /info is the human/health endpoint. NOT "/" — MCP claims that
        # path for session resumption per Streamable HTTP.
        resp = app_with_backend.get("/info")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "iris-mcp"
        assert data["endpoint"] == "/"
        assert data["backend"] == "http://iris-backend.test"

    def test_info_includes_package_version(
        self, app_with_backend: TestClient,
    ) -> None:
        """v5.8.4: /info reports the iris-mcp package version so a deploy
        can be identified by URL probe rather than behaviour inference.

        Read via importlib.metadata at request time; matches the version
        set in mcp/pyproject.toml. We don't pin to a specific string
        because the package version moves with each iris-mcp release —
        just assert the field exists and looks like a semver-ish string.
        """
        resp = app_with_backend.get("/info")
        data = resp.json()
        assert "version" in data
        # Package version source-of-truth is mcp/pyproject.toml; aligned
        # with iris release versioning from v5.8.4 onwards.
        assert isinstance(data["version"], str)
        # At least one dot separator (e.g., "5.8.4", "5.9.0").
        assert "." in data["version"]


class TestFavicon:
    def test_favicon_ico_returns_iris_eye_svg(
        self, app_with_backend: TestClient,
    ) -> None:
        # Registered before the root mount so it isn't swallowed.
        resp = app_with_backend.get("/favicon.ico")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/svg+xml"
        assert resp.content.startswith(b"<svg")
        assert b"#0ea5e9" in resp.content  # iris brand sky blue

    def test_favicon_svg_returns_iris_eye_svg(
        self, app_with_backend: TestClient,
    ) -> None:
        resp = app_with_backend.get("/favicon.svg")
        assert resp.status_code == 200
        assert resp.content.startswith(b"<svg")


class TestRootMount:
    def test_post_root_does_not_307(self, app_with_backend: TestClient) -> None:
        """ADR-134 follow-up: MCP is mounted at /, so the user pastes the bare
        service URL. No /mcp suffix means no slash-redirect to chase."""
        resp = app_with_backend.post(
            "/",
            headers={"accept": "application/json, text/event-stream"},
            follow_redirects=False,
        )
        assert resp.status_code != 307, "POST / must not redirect"
        # Response is a real MCP error/result, not a 405 from FastAPI —
        # confirms the ASGI mount is the one handling it.
        assert resp.status_code != 405


class TestCreateAppFetchesInstructions:
    """ADR-165 / issue #119: the HTTP transport must fetch the orient-
    first protocol body in its startup lifespan and attach it to the
    wrapped MCP server's `instructions` attribute. Without this wiring,
    claude.ai connects and gets InitializeResult with no `instructions`
    body — the model can't see the "INVOKE the structural-overview
    call... NOT as a follow-up 'want me to load it?' prompt" directive,
    and the user-visible flow regresses to a paraphrased text menu.

    The fetch lives in the lifespan (not `create_app` directly) so the
    factory stays sync-callable from async test contexts; tests enter
    the lifespan via TestClient's context manager to trigger startup.
    """

    def test_lifespan_fetches_and_wires_instructions(
        self,
        monkeypatch: pytest.MonkeyPatch,
        respx_mock: respx.Router,
    ) -> None:
        monkeypatch.setenv("IRIS_API_URL", "http://iris.test")
        respx_mock.get("http://iris.test/api/ai/server-instructions").mock(
            return_value=httpx.Response(200, json={"body": "ORIENT BODY"}),
        )
        from iris_mcp.http_main import create_app

        app = create_app()
        # SPEC-165-A: session_manager attached to app.state so the
        # regression test can inspect the wrapped server's instructions
        # without resorting to private FastAPI route walking.
        with TestClient(app):
            # Lifespan startup ran inside __enter__; instructions are now
            # wired into the wrapped MCP server.
            sm = app.state.session_manager
            assert sm.app.instructions == "ORIENT BODY"

    def test_lifespan_falls_back_when_backend_unreachable(
        self,
        monkeypatch: pytest.MonkeyPatch,
        respx_mock: respx.Router,
    ) -> None:
        monkeypatch.setenv("IRIS_API_URL", "http://iris.test")
        respx_mock.get("http://iris.test/api/ai/server-instructions").mock(
            side_effect=httpx.ConnectError("connection refused"),
        )
        from iris_mcp.http_main import create_app
        from iris_mcp.server_instructions import _FALLBACK_INSTRUCTIONS

        app = create_app()
        with TestClient(app):
            sm = app.state.session_manager
            # Never None in production — fall through always yields the
            # hardcoded safe baseline. Pins the contract that the HTTP
            # transport advertises *some* orient body even in degraded
            # backend states.
            assert sm.app.instructions == _FALLBACK_INSTRUCTIONS
            assert "ORIENT-FIRST PROTOCOL" in sm.app.instructions

    def test_lifespan_falls_back_on_http_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        respx_mock: respx.Router,
    ) -> None:
        monkeypatch.setenv("IRIS_API_URL", "http://iris.test")
        monkeypatch.setenv("IRIS_MCP_INSTRUCTIONS_REFRESH_S", "0")
        respx_mock.get("http://iris.test/api/ai/server-instructions").mock(
            return_value=httpx.Response(500, json={"detail": "boom"}),
        )
        from iris_mcp.http_main import create_app
        from iris_mcp.server_instructions import _FALLBACK_INSTRUCTIONS

        app = create_app()
        with TestClient(app):
            sm = app.state.session_manager
            assert sm.app.instructions == _FALLBACK_INSTRUCTIONS


class TestRefreshLoop:
    """ADR-166 / SPEC-166-A: TTL background refresh so admin edits to
    `mcp_server_instructions` propagate to claude.ai without requiring
    a Render redeploy. Tests use a short refresh interval so the loop
    runs multiple times during the test window.
    """

    def test_lifespan_picks_up_updated_body(
        self,
        monkeypatch: pytest.MonkeyPatch,
        respx_mock: respx.Router,
    ) -> None:
        # 50ms refresh — fast enough to land within the test window,
        # slow enough that the initial startup fetch settles before the
        # first refresh tick (avoids racy "did the loop run yet?" reads).
        monkeypatch.setenv("IRIS_API_URL", "http://iris.test")
        monkeypatch.setenv("IRIS_MCP_INSTRUCTIONS_REFRESH_S", "0.05")
        # First call: lifespan startup. Subsequent: refresh ticks see
        # the new body — simulating an admin edit landing mid-session.
        respx_mock.get("http://iris.test/api/ai/server-instructions").mock(
            side_effect=[
                httpx.Response(200, json={"body": "BOOT BODY"}),
                httpx.Response(200, json={"body": "ADMIN-EDITED BODY"}),
                httpx.Response(200, json={"body": "ADMIN-EDITED BODY"}),
                httpx.Response(200, json={"body": "ADMIN-EDITED BODY"}),
                httpx.Response(200, json={"body": "ADMIN-EDITED BODY"}),
            ],
        )
        from iris_mcp.http_main import create_app

        app = create_app()
        with TestClient(app):
            sm = app.state.session_manager
            assert sm.app.instructions == "BOOT BODY"
            # Poll for the refresh — up to 1 second.
            for _ in range(20):
                if sm.app.instructions == "ADMIN-EDITED BODY":
                    break
                time.sleep(0.05)
            assert sm.app.instructions == "ADMIN-EDITED BODY"

    def test_lifespan_preserves_body_on_transient_failure(
        self,
        monkeypatch: pytest.MonkeyPatch,
        respx_mock: respx.Router,
    ) -> None:
        """Failed refreshes must NOT clobber the previously-fetched body
        with the fallback baseline — that would silently revert admin
        customisations any time the backend hiccups for >REFRESH_S."""
        from iris_mcp.server_instructions import _FALLBACK_INSTRUCTIONS

        monkeypatch.setenv("IRIS_API_URL", "http://iris.test")
        monkeypatch.setenv("IRIS_MCP_INSTRUCTIONS_REFRESH_S", "0.05")
        call_count = [0]

        def _side_effect(request: httpx.Request) -> httpx.Response:
            call_count[0] += 1
            if call_count[0] == 1:
                return httpx.Response(200, json={"body": "GOOD BODY"})
            # Every subsequent call simulates a transient backend
            # failure — refresh loop should preserve the boot body.
            raise httpx.ConnectError("backend down")

        respx_mock.get("http://iris.test/api/ai/server-instructions").mock(
            side_effect=_side_effect,
        )
        from iris_mcp.http_main import create_app

        app = create_app()
        with TestClient(app):
            sm = app.state.session_manager
            assert sm.app.instructions == "GOOD BODY"
            # Wait long enough for several failed refresh ticks.
            time.sleep(0.3)
            assert sm.app.instructions == "GOOD BODY"
            # Specifically, never clobbered with the hardcoded fallback.
            assert sm.app.instructions != _FALLBACK_INSTRUCTIONS
            # Sanity: the refresh loop actually fired more than once.
            assert call_count[0] >= 2

    def test_refresh_disabled_when_interval_zero(
        self,
        monkeypatch: pytest.MonkeyPatch,
        respx_mock: respx.Router,
    ) -> None:
        """`IRIS_MCP_INSTRUCTIONS_REFRESH_S=0` short-circuits the loop —
        only the startup fetch runs. Useful for deterministic tests and
        for ops who don't want background traffic to their backend."""
        monkeypatch.setenv("IRIS_API_URL", "http://iris.test")
        monkeypatch.setenv("IRIS_MCP_INSTRUCTIONS_REFRESH_S", "0")
        route = respx_mock.get(
            "http://iris.test/api/ai/server-instructions",
        ).mock(return_value=httpx.Response(200, json={"body": "ONCE"}))
        from iris_mcp.http_main import create_app

        app = create_app()
        with TestClient(app):
            time.sleep(0.2)
            sm = app.state.session_manager
            assert sm.app.instructions == "ONCE"
            # Only the lifespan startup fetch ran — no refresh ticks.
            assert route.call_count == 1
