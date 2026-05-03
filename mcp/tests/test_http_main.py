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


class TestRootRoute:
    def test_root_returns_service_identity(
        self, app_with_backend: TestClient,
    ) -> None:
        resp = app_with_backend.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "iris-mcp"
        assert data["endpoint"] == "/mcp/"
        assert data["backend"] == "http://iris-backend.test"


class TestFavicon:
    def test_favicon_ico_returns_iris_eye_svg(
        self, app_with_backend: TestClient,
    ) -> None:
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


class TestMcpPathNormalisation:
    def test_bare_mcp_does_not_307(self, app_with_backend: TestClient) -> None:
        """ADR-134 / SPEC-134-A: bare /mcp must not 307 — some clients drop POST body on redirect."""
        # Send a POST without any body — we don't care about the MCP
        # response correctness here, only that the path normalisation
        # middleware sent us straight to the mount instead of 307'ing.
        resp = app_with_backend.post(
            "/mcp",
            headers={"accept": "application/json, text/event-stream"},
            follow_redirects=False,
        )
        assert resp.status_code != 307, "bare /mcp must not redirect"
