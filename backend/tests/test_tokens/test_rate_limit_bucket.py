"""Unit tests for the PAT-aware rate-limit categoriser (ADR-127 / ADR-129).

The categoriser is pure — no DB — so we test it directly with a synthesised
Starlette `Request`.
"""

from __future__ import annotations

from starlette.requests import Request

from app.middleware.rate_limit import _get_rate_category


def _req(path: str, auth: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if auth is not None:
        headers.append((b"authorization", auth.encode()))
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "raw_path": path.encode(),
        "headers": headers,
        "query_string": b"",
    }
    return Request(scope)


class TestCategoriser:
    def test_login_bucket(self) -> None:
        assert _get_rate_category(_req("/api/auth/login")) == "login"

    def test_refresh_bucket(self) -> None:
        assert _get_rate_category(_req("/api/auth/refresh")) == "refresh"

    def test_anon_ai_bucket(self) -> None:
        # No Authorization, an actual AI-provider-calling path → anon_ai.
        assert _get_rate_category(_req("/api/ai/ask")) == "anon_ai"

    def test_anon_ai_bucket_covers_set_scoped_ask(self) -> None:
        assert (
            _get_rate_category(_req("/api/ai/sets/abc-123/ask")) == "anon_ai"
        )

    def test_non_ask_ai_paths_use_anon_not_anon_ai(self) -> None:
        # Regression (ADR-246): these are plain DB reads with no AI-provider
        # call, so a path-prefix match on `/api/ai/*` alone wrongly swept
        # them into the 10/hour anon_ai bucket — shared globally by every
        # anonymous caller including iris-mcp's per-session
        # GET /api/ai/server-instructions (ADR-163). They belong in the
        # much larger `anon` bucket instead.
        for path in (
            "/api/ai/server-instructions",
            "/api/ai/providers/active",
            "/api/ai/files/extract",
            "/api/ai/usage",
        ):
            assert _get_rate_category(_req(path)) == "anon", path

    def test_pat_bucket(self) -> None:
        assert _get_rate_category(_req("/api/search", auth="Bearer iris_pat_x")) == "pat"

    def test_anon_bucket(self) -> None:
        # No Authorization, non-AI path → anon.
        assert _get_rate_category(_req("/api/search")) == "anon"

    def test_general_for_jwt(self) -> None:
        # JWT-ish Bearer that is not a PAT → general.
        assert _get_rate_category(_req("/api/search", auth="Bearer eyJabc.def.ghi")) == "general"

    def test_pat_preferred_over_anon_ai_for_ai_path(self) -> None:
        # A PAT-authenticated AI call uses the `pat` bucket, not `anon_ai`.
        assert (
            _get_rate_category(_req("/api/ai/ask", auth="Bearer iris_pat_x"))
            == "pat"
        )
