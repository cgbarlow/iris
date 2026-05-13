"""build_server `instructions` wiring tests (ADR-163, SPEC-163-A).

Verifies the MCP SDK's `Server(instructions=...)` constructor
receives the value passed through `build_server(client, instructions=...)`
and that omitting the kwarg yields `instructions=None`.
"""

from __future__ import annotations

import pytest
from iris_client import IrisClient

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
