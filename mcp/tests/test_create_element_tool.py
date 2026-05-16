"""v6.4.0: MCP create_element tool test (ADR-180 follow-up).

Backfills MCP element creation parity — previously elements could
only be created via apply_diagram_creation (atomic with a diagram
canvas). v6.4.0 adds a standalone create_element for the
element-pool use case.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from iris_client import IrisClient

from iris_mcp import tools

BASE = "http://iris.test"


class TestInventory:
    def test_create_element_registered(self) -> None:
        names = {t.name for t in tools.tool_definitions()}
        assert "create_element" in names

    def test_create_element_schema_requires_type_and_name(self) -> None:
        defs = {t.name: t for t in tools.tool_definitions()}
        schema = defs["create_element"].inputSchema
        assert set(schema["required"]) == {"element_type", "name"}


class TestCreateElement:
    @pytest.mark.asyncio
    async def test_happy(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.post(f"{BASE}/api/elements").mock(
            return_value=httpx.Response(201, json={
                "id": "el-1", "element_type": "component",
                "name": "Widget", "current_version": 1,
                "notation": "simple", "set_id": "s-1",
                "created_at": "2026", "updated_at": "2026", "data": {},
            }),
        )
        result = await tools.dispatch(
            "create_element", client,
            {
                "element_type": "component",
                "name": "Widget",
                "set_id": "s-1",
                "notation": "simple",
            },
        )
        body = json.loads(result[0].text)
        assert body["id"] == "el-1"
        post_body = json.loads(route.calls[0].request.content)
        assert post_body["element_type"] == "component"
        assert post_body["name"] == "Widget"
        assert post_body["set_id"] == "s-1"

    @pytest.mark.asyncio
    async def test_401_returns_auth_required(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(f"{BASE}/api/elements").mock(
            return_value=httpx.Response(401, json={"detail": "no auth"}),
        )
        result = await tools.dispatch(
            "create_element", client,
            {"element_type": "component", "name": "X"},
        )
        body = json.loads(result[0].text)
        assert body["success"] is False
        assert body["error"] == "auth_required"
