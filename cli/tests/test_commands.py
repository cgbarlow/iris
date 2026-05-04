"""Command surface tests using Typer's CliRunner + respx."""

from __future__ import annotations

import json

import httpx
import respx
from typer.testing import CliRunner

from iris_cli.main import app

runner = CliRunner()
BASE = "http://iris.test"


def _invoke(*args: str) -> tuple[int, str, str]:
    result = runner.invoke(app, list(args), catch_exceptions=False)
    return result.exit_code, result.stdout, result.stderr


class TestSearch:
    def test_search_table_output(self, respx_mock: respx.Router) -> None:
        respx_mock.get(f"{BASE}/api/search").mock(
            return_value=httpx.Response(200, json={
                "query": "payment",
                "results": [
                    {"id": "e1", "result_type": "element", "name": "PaymentSvc"},
                ],
                "total": 1,
            }),
        )
        code, out, _ = _invoke("search", "payment")
        assert code == 0
        assert "PaymentSvc" in out

    def test_search_json_flag(self, respx_mock: respx.Router) -> None:
        respx_mock.get(f"{BASE}/api/search").mock(
            return_value=httpx.Response(200, json={
                "query": "x", "results": [], "total": 0,
            }),
        )
        code, out, _ = _invoke("--json", "search", "x")
        assert code == 0
        parsed = json.loads(out)
        assert parsed["query"] == "x"
        assert parsed["total"] == 0


class TestDiagrams:
    def test_list(self, respx_mock: respx.Router) -> None:
        respx_mock.get(f"{BASE}/api/diagrams").mock(
            return_value=httpx.Response(200, json=[{
                "id": "d1", "name": "Flow", "diagram_type": "simple",
                "current_version": 1, "notation": "simple",
                "created_at": "2026-01-01", "updated_at": "2026-01-01", "data": {},
            }]),
        )
        code, out, _ = _invoke("diagrams", "list")
        assert code == 0
        assert "Flow" in out

    def test_get(self, respx_mock: respx.Router) -> None:
        respx_mock.get(f"{BASE}/api/diagrams/d1").mock(
            return_value=httpx.Response(200, json={
                "id": "d1", "name": "Flow", "diagram_type": "simple",
                "current_version": 1, "notation": "simple",
                "created_at": "2026-01-01", "updated_at": "2026-01-01", "data": {},
            }),
        )
        code, out, _ = _invoke("diagrams", "get", "d1")
        assert code == 0
        assert "d1" in out


class TestExport:
    def test_export_writes_file(
        self, respx_mock: respx.Router, tmp_path: object,
    ) -> None:
        respx_mock.get(f"{BASE}/api/export/diagrams/d1").mock(
            return_value=httpx.Response(
                200, content=b"# Flow\n",
                headers={"content-type": "text/markdown; charset=utf-8"},
            ),
        )
        out_path = tmp_path / "flow.md"  # type: ignore[operator]
        code, _out, _ = _invoke(
            "export", "diagram", "d1", "--format", "markdown", "-o", str(out_path),
        )
        assert code == 0
        assert out_path.read_bytes() == b"# Flow\n"


class TestErrorHandling:
    def test_auth_error_exits_3(self, respx_mock: respx.Router) -> None:
        respx_mock.get(f"{BASE}/api/auth/me").mock(
            return_value=httpx.Response(401, json={"detail": "Not authenticated"}),
        )
        # Provide a token so the client actually makes the call (anonymous
        # whoami short-circuits to a client-side response).
        code, _, err = _invoke(
            "--token", "iris_pat_bogus", "whoami",
        )
        assert code == 3
        assert "Not authenticated" in err or "run `iris login`" in err

    def test_404_exits_1(self, respx_mock: respx.Router) -> None:
        respx_mock.get(f"{BASE}/api/diagrams/missing").mock(
            return_value=httpx.Response(404, json={"detail": "Not found"}),
        )
        code, _, err = _invoke("diagrams", "get", "missing")
        assert code == 1
        assert "Not found" in err


class TestLoginCommand:
    def test_login_saves_config(
        self, respx_mock: respx.Router, tmp_path: object,
        monkeypatch: object,
    ) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))  # type: ignore[attr-defined]
        respx_mock.post(f"{BASE}/api/auth/login").mock(
            return_value=httpx.Response(200, json={
                "access_token": "jwt-xyz", "refresh_token": "r", "token_type": "bearer",
            }),
        )
        respx_mock.post(f"{BASE}/api/users/me/tokens").mock(
            return_value=httpx.Response(201, json={
                "id": "pat-1", "name": "test", "prefix": "ab",
                "created_at": "2026-01-01",
                "token": "iris_pat_ab_secret",
            }),
        )

        code, _out, _ = _invoke(
            "login",
            "--username", "alice",
            "--password", "pw",
        )
        assert code == 0
        saved = (tmp_path / "iris" / "config.toml").read_text()  # type: ignore[operator]
        assert 'token = "iris_pat_ab_secret"' in saved

    def test_login_with_token_flag_skips_api_call(
        self, respx_mock: respx.Router, tmp_path: object,
        monkeypatch: object,
    ) -> None:
        """Supabase-mode path: --token <PAT> just persists config, no /auth/login call."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))  # type: ignore[attr-defined]
        # Deliberately mock NOTHING — if the CLI attempts an API call,
        # respx will raise on the unmatched request and the test fails.

        code, out, _ = _invoke(
            "login",
            "--url", BASE,
            "--token", "iris_pat_xy_secret",
        )
        assert code == 0, out
        saved = (tmp_path / "iris" / "config.toml").read_text()  # type: ignore[operator]
        assert 'token = "iris_pat_xy_secret"' in saved
        assert f'url = "{BASE}"' in saved

    def test_login_supabase_mode_404_gives_actionable_error(
        self, respx_mock: respx.Router, tmp_path: object,
        monkeypatch: object,
    ) -> None:
        """Hitting /api/auth/login on a Supabase backend should fail loudly with --token guidance."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))  # type: ignore[attr-defined]
        respx_mock.post(f"{BASE}/api/auth/login").mock(
            return_value=httpx.Response(404, json={
                "detail": (
                    "This endpoint is not available in Supabase deployment "
                    "mode. Use Supabase Auth for authentication."
                ),
            }),
        )

        code, _out, _ = _invoke(
            "login",
            "--username", "alice",
            "--password", "pw",
        )
        assert code == 1  # exit code 1 per actionable-error path
