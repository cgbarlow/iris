"""build_server / build_session_manager `instructions` wiring tests
(ADR-163, SPEC-163-A; ADR-165, SPEC-165-A).

Verifies the MCP SDK's `Server(instructions=...)` constructor
receives the value passed through `build_server(client, instructions=...)`
(stdio path) AND through `build_session_manager(instructions=...)`
(HTTP path). Both transports must advertise `instructions` on
`InitializeResult` so the orient-first protocol reaches every
connected MCP client. Issue #119 covers the HTTP-side regression.
"""

from __future__ import annotations

import pytest
from iris_client import IrisClient

from iris_mcp.asgi import build_session_manager
from iris_mcp.server import build_server


@pytest.fixture
async def client() -> IrisClient:
    async with IrisClient(url="http://iris.test", token=None) as c:
        yield c


class TestBuildServerInstructionsWiring:
    @pytest.mark.asyncio
    async def test_instructions_passed_through(
        self, client: IrisClient,
    ) -> None:
        server = build_server(client, instructions="HELLO INSTRUCTIONS")
        assert server.instructions == "HELLO INSTRUCTIONS"

    @pytest.mark.asyncio
    async def test_no_instructions_kwarg_yields_none(
        self, client: IrisClient,
    ) -> None:
        server = build_server(client)
        assert server.instructions is None

    @pytest.mark.asyncio
    async def test_explicit_none_yields_none(
        self, client: IrisClient,
    ) -> None:
        server = build_server(client, instructions=None)
        assert server.instructions is None


class TestBuildSessionManagerInstructionsWiring:
    """ADR-165 / issue #119: the HTTP transport must round-trip the
    same `instructions` body the stdio transport already does."""

    def test_instructions_passed_through(self) -> None:
        sm = build_session_manager(instructions="HTTP HELLO")
        # StreamableHTTPSessionManager.app is the wrapped MCP Server;
        # `server.instructions` is what the SDK serialises into the
        # InitializeResult that every MCP client reads on connect.
        assert sm.app.instructions == "HTTP HELLO"

    def test_no_instructions_kwarg_yields_none(self) -> None:
        sm = build_session_manager()
        assert sm.app.instructions is None

    def test_explicit_none_yields_none(self) -> None:
        sm = build_session_manager(instructions=None)
        assert sm.app.instructions is None
