"""server_instructions tests (ADR-163, SPEC-163-A).

Verifies `fetch_server_instructions` returns the backend body on a
happy fetch and falls back to the hardcoded baseline on any failure
mode (network error, HTTP error, malformed JSON, empty body).
"""

from __future__ import annotations

import httpx
import pytest
import respx

from iris_mcp.server_instructions import (
    _FALLBACK_INSTRUCTIONS,
    fetch_server_instructions,
    try_fetch_server_instructions,
)

BASE = "http://iris.test"


class TestFetchServerInstructions:
    @pytest.mark.asyncio
    async def test_happy_fetch_returns_body(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/ai/server-instructions").mock(
            return_value=httpx.Response(
                200, json={"body": "ADMIN-EDITED INSTRUCTIONS"},
            ),
        )
        result = await fetch_server_instructions(BASE)
        assert result == "ADMIN-EDITED INSTRUCTIONS"

    @pytest.mark.asyncio
    async def test_empty_body_falls_back(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/ai/server-instructions").mock(
            return_value=httpx.Response(200, json={"body": ""}),
        )
        result = await fetch_server_instructions(BASE)
        assert result == _FALLBACK_INSTRUCTIONS

    @pytest.mark.asyncio
    async def test_whitespace_body_falls_back(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/ai/server-instructions").mock(
            return_value=httpx.Response(200, json={"body": "   \n   "}),
        )
        result = await fetch_server_instructions(BASE)
        assert result == _FALLBACK_INSTRUCTIONS

    @pytest.mark.asyncio
    async def test_http_error_falls_back(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/ai/server-instructions").mock(
            return_value=httpx.Response(500, json={"detail": "boom"}),
        )
        result = await fetch_server_instructions(BASE)
        assert result == _FALLBACK_INSTRUCTIONS

    @pytest.mark.asyncio
    async def test_404_falls_back(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/ai/server-instructions").mock(
            return_value=httpx.Response(404, json={"detail": "not found"}),
        )
        result = await fetch_server_instructions(BASE)
        assert result == _FALLBACK_INSTRUCTIONS

    @pytest.mark.asyncio
    async def test_network_error_falls_back(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/ai/server-instructions").mock(
            side_effect=httpx.ConnectError("connection refused"),
        )
        result = await fetch_server_instructions(BASE)
        assert result == _FALLBACK_INSTRUCTIONS

    @pytest.mark.asyncio
    async def test_malformed_json_falls_back(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/ai/server-instructions").mock(
            return_value=httpx.Response(
                200,
                text="not json",
                headers={"content-type": "application/json"},
            ),
        )
        result = await fetch_server_instructions(BASE)
        assert result == _FALLBACK_INSTRUCTIONS

    @pytest.mark.asyncio
    async def test_fallback_contains_protocol_markers(self) -> None:
        # Fallback must mirror the seeded body for landing-safety
        # when the backend is unreachable.
        assert "ORIENT-FIRST PROTOCOL" in _FALLBACK_INSTRUCTIONS
        assert "DISCOVERY TOOLS" in _FALLBACK_INSTRUCTIONS
        assert "WORKFLOW GUIDANCE" in _FALLBACK_INSTRUCTIONS
        assert "AUTH RECOVERY" in _FALLBACK_INSTRUCTIONS


class TestTryFetchServerInstructions:
    """ADR-166 / SPEC-166-A: `try_fetch_server_instructions` is the
    refresh-loop variant of `fetch_server_instructions` — returns
    `None` on every failure mode the canonical variant falls back from,
    so the refresh loop can distinguish "real new body" from "backend
    transiently unavailable" and preserve the last good value rather
    than clobber it with the fallback baseline.
    """

    @pytest.mark.asyncio
    async def test_happy_fetch_returns_body(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/ai/server-instructions").mock(
            return_value=httpx.Response(
                200, json={"body": "ADMIN-EDITED INSTRUCTIONS"},
            ),
        )
        result = await try_fetch_server_instructions(BASE)
        assert result == "ADMIN-EDITED INSTRUCTIONS"

    @pytest.mark.asyncio
    async def test_empty_body_returns_none(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/ai/server-instructions").mock(
            return_value=httpx.Response(200, json={"body": ""}),
        )
        result = await try_fetch_server_instructions(BASE)
        assert result is None

    @pytest.mark.asyncio
    async def test_whitespace_body_returns_none(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/ai/server-instructions").mock(
            return_value=httpx.Response(200, json={"body": "   \n   "}),
        )
        result = await try_fetch_server_instructions(BASE)
        assert result is None

    @pytest.mark.asyncio
    async def test_http_error_returns_none(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/ai/server-instructions").mock(
            return_value=httpx.Response(500, json={"detail": "boom"}),
        )
        result = await try_fetch_server_instructions(BASE)
        assert result is None

    @pytest.mark.asyncio
    async def test_404_returns_none(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/ai/server-instructions").mock(
            return_value=httpx.Response(404, json={"detail": "not found"}),
        )
        result = await try_fetch_server_instructions(BASE)
        assert result is None

    @pytest.mark.asyncio
    async def test_network_error_returns_none(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/ai/server-instructions").mock(
            side_effect=httpx.ConnectError("connection refused"),
        )
        result = await try_fetch_server_instructions(BASE)
        assert result is None

    @pytest.mark.asyncio
    async def test_malformed_json_returns_none(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/ai/server-instructions").mock(
            return_value=httpx.Response(
                200,
                text="not json",
                headers={"content-type": "application/json"},
            ),
        )
        result = await try_fetch_server_instructions(BASE)
        assert result is None
