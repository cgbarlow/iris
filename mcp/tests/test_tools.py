"""Tool-dispatch tests for iris-mcp."""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from iris_client import IrisClient

from iris_mcp import tools

BASE = "http://iris.test"


class TestInventory:
    def test_every_tool_has_description(self) -> None:
        defs = tools.tool_definitions()
        assert len(defs) >= 19  # Sanity — SPEC-131-A targets ~19-24 tools.
        for t in defs:
            assert t.name
            assert t.description
            assert len(t.description) >= 15


class TestDispatchSearch:
    @pytest.mark.asyncio
    async def test_search_happy(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/search").mock(
            return_value=httpx.Response(200, json={
                "query": "payment", "results": [], "total": 0,
            }),
        )
        result = await tools.dispatch("search", client, {"query": "payment"})
        assert len(result) == 1
        body = json.loads(result[0].text)
        assert body["query"] == "payment"

    @pytest.mark.asyncio
    async def test_search_http_error_formatted(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/search").mock(
            return_value=httpx.Response(429, json={"detail": "Too many requests"}),
        )
        result = await tools.dispatch("search", client, {"query": "x"})
        assert result[0].text.startswith("ERROR:")
        assert "Rate-limited" in result[0].text


class TestExport:
    @pytest.mark.asyncio
    async def test_export_diagram_markdown(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/export/diagrams/d1").mock(
            return_value=httpx.Response(200, content=b"# Overview\n"),
        )
        result = await tools.dispatch(
            "export_diagram", client, {"diagram_id": "d1", "format": "markdown"},
        )
        assert result[0].text == "# Overview\n"


class TestAskRemoved:
    """v6.0.8 (ADR-168): the `ask` tool was removed from the MCP
    surface. When iris-mcp is consumed by a capable LLM client
    (claude.ai / Claude Desktop / Claude Code / Cursor), routing
    cross-scope questions to Iris' server-side AI is redundant — the
    local model walks the data itself via the read-only tools."""

    def test_ask_not_in_tool_definitions(self) -> None:
        names = {t.name for t in tools.tool_definitions()}
        assert "ask" not in names

    @pytest.mark.asyncio
    async def test_ask_dispatch_returns_unknown_tool_error(
        self, client: IrisClient,
    ) -> None:
        result = await tools.dispatch("ask", client, {"question": "?"})
        assert result[0].text.startswith("ERROR: unknown tool")


class TestUnknownTool:
    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(
        self, client: IrisClient,
    ) -> None:
        result = await tools.dispatch("not_a_tool", client, {})
        assert result[0].text.startswith("ERROR: unknown tool")
