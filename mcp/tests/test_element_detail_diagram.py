"""MCP tests for the v6.33.0 element ``detail_diagram_id`` field
(ADR-221, issue #242).

Asserts the create + update tool schemas advertise ``detail_diagram_id``
and that the handlers forward it (create: non-null only; update:
tri-state including JSON null for clear).
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from iris_client import IrisClient

from iris_mcp import tools

BASE = "http://iris.test"


def _element_response(**overrides):
    base = {
        "id": "el1",
        "element_type": "component",
        "current_version": 1,
        "name": "Cap",
        "description": None,
        "data": {},
        "set_id": "s1",
        "package_id": None,
        "package_name": None,
        "detail_diagram_id": None,
        "notation": "simple",
        "created_at": "2026-05-29T00:00:00+00:00",
        "created_by": "u",
        "updated_at": "2026-05-29T00:00:00+00:00",
    }
    base.update(overrides)
    return base


class TestSchema:
    def test_create_and_update_schemas_include_detail_diagram_id(self) -> None:
        defs = {t.name: t for t in tools.tool_definitions()}
        for tool_name in ("create_element", "update_element"):
            props = defs[tool_name].inputSchema["properties"]
            assert "detail_diagram_id" in props, tool_name
            assert "detail_diagram_id" not in defs[tool_name].inputSchema.get(
                "required", [],
            )


class TestCreateForwarding:
    @pytest.mark.anyio
    async def test_forwards_detail_diagram_id(
        self, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.post(f"{BASE}/api/elements").mock(
            return_value=httpx.Response(
                201, json=_element_response(detail_diagram_id="d1"),
            ),
        )
        async with IrisClient(BASE) as c:
            await tools._create_element(
                c,
                {
                    "element_type": "component",
                    "name": "Cap",
                    "set_id": "s1",
                    "detail_diagram_id": "d1",
                },
            )
        body = json.loads(route.calls[0].request.content)
        assert body["detail_diagram_id"] == "d1"

    @pytest.mark.anyio
    async def test_omitting_keeps_it_out_of_body(
        self, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.post(f"{BASE}/api/elements").mock(
            return_value=httpx.Response(201, json=_element_response()),
        )
        async with IrisClient(BASE) as c:
            await tools._create_element(
                c, {"element_type": "component", "name": "Cap", "set_id": "s1"},
            )
        body = json.loads(route.calls[0].request.content)
        assert "detail_diagram_id" not in body


class TestUpdateForwarding:
    @pytest.mark.anyio
    async def test_sets_detail_diagram_id(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/elements/el1").mock(
            return_value=httpx.Response(200, json=_element_response()),
        )
        put = respx_mock.put(f"{BASE}/api/elements/el1").mock(
            return_value=httpx.Response(
                200, json=_element_response(detail_diagram_id="d1", current_version=2),
            ),
        )
        async with IrisClient(BASE) as c:
            await tools._update_element(
                c, {"element_id": "el1", "detail_diagram_id": "d1"},
            )
        body = json.loads(put.calls[0].request.content)
        assert body["detail_diagram_id"] == "d1"

    @pytest.mark.anyio
    async def test_clears_detail_diagram_id_with_null(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/elements/el1").mock(
            return_value=httpx.Response(
                200, json=_element_response(detail_diagram_id="d1"),
            ),
        )
        put = respx_mock.put(f"{BASE}/api/elements/el1").mock(
            return_value=httpx.Response(
                200, json=_element_response(detail_diagram_id=None, current_version=2),
            ),
        )
        async with IrisClient(BASE) as c:
            await tools._update_element(
                c, {"element_id": "el1", "detail_diagram_id": None},
            )
        body = json.loads(put.calls[0].request.content)
        assert "detail_diagram_id" in body
        assert body["detail_diagram_id"] is None
