"""Tests for the standalone iris-mcp HTTP service (SPEC-134-A)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_with_backend(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("IRIS_API_URL", "http://iris-backend.test")
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
