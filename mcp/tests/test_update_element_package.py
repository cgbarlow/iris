"""MCP tests for the ADR-184 element ↔ package surface (v6.7.0).

Covers:
- ``update_element`` accepts ``package_id`` (set + clear via null).
- ``list_elements`` forwards ``package_id`` to the backend, including
  the literal ``"null"`` sentinel.
- New tool ``list_package_elements`` round-trips through
  ``GET /api/packages/{id}/elements``.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from iris_client import IrisClient

from iris_mcp import tools

BASE = "http://iris.test"


def _element(**overrides):
    base = {
        "id": "el1",
        "element_type": "component",
        "current_version": 1,
        "name": "E",
        "description": None,
        "data": {},
        "set_id": "s1",
        "package_id": None,
        "package_name": None,
        "notation": "simple",
        "created_at": "2026-05-16T00:00:00+00:00",
        "created_by": "u",
        "updated_at": "2026-05-16T00:00:00+00:00",
    }
    base.update(overrides)
    return base


class TestInventory:
    def test_list_package_elements_tool_registered(self) -> None:
        names = {t.name for t in tools.tool_definitions()}
        assert "list_package_elements" in names

    def test_update_element_schema_includes_package_id(self) -> None:
        defs = {t.name: t for t in tools.tool_definitions()}
        props = defs["update_element"].inputSchema["properties"]
        assert "package_id" in props

    def test_list_elements_schema_includes_package_id(self) -> None:
        defs = {t.name: t for t in tools.tool_definitions()}
        props = defs["list_elements"].inputSchema["properties"]
        assert "package_id" in props


class TestUpdateElementPackage:
    @pytest.mark.anyio
    async def test_set_package_id(self, respx_mock: respx.Router) -> None:
        respx_mock.get(f"{BASE}/api/elements/el1").mock(
            return_value=httpx.Response(200, json=_element()),
        )
        put_route = respx_mock.put(f"{BASE}/api/elements/el1").mock(
            return_value=httpx.Response(200, json=_element(package_id="p1")),
        )
        async with IrisClient(BASE) as c:
            payload = await tools._update_element(
                c, {"element_id": "el1", "package_id": "p1"},
            )
        body = json.loads(put_route.calls[0].request.content)
        assert body["package_id"] == "p1"
        # Result text should mention the package id.
        assert "p1" in payload

    @pytest.mark.anyio
    async def test_clear_package_id_with_null(self, respx_mock: respx.Router) -> None:
        respx_mock.get(f"{BASE}/api/elements/el1").mock(
            return_value=httpx.Response(200, json=_element(package_id="p1")),
        )
        put_route = respx_mock.put(f"{BASE}/api/elements/el1").mock(
            return_value=httpx.Response(200, json=_element(package_id=None)),
        )
        async with IrisClient(BASE) as c:
            await tools._update_element(
                c, {"element_id": "el1", "package_id": None},
            )
        body = json.loads(put_route.calls[0].request.content)
        assert body["package_id"] is None

    @pytest.mark.anyio
    async def test_omitting_package_id_leaves_field_alone(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/elements/el1").mock(
            return_value=httpx.Response(200, json=_element(package_id="p1")),
        )
        put_route = respx_mock.put(f"{BASE}/api/elements/el1").mock(
            return_value=httpx.Response(200, json=_element(package_id="p1")),
        )
        async with IrisClient(BASE) as c:
            await tools._update_element(
                c, {"element_id": "el1", "name": "Renamed"},
            )
        body = json.loads(put_route.calls[0].request.content)
        assert "package_id" not in body


class TestListElementsFilter:
    @pytest.mark.anyio
    async def test_forwards_package_id(self, respx_mock: respx.Router) -> None:
        route = respx_mock.get(f"{BASE}/api/elements").mock(
            return_value=httpx.Response(
                200, json={"items": [_element(package_id="p1")], "total": 1,
                           "page": 1, "page_size": 50},
            ),
        )
        async with IrisClient(BASE) as c:
            await tools._list_elements(c, {"package_id": "p1"})
        assert "package_id=p1" in str(route.calls[0].request.url)

    @pytest.mark.anyio
    async def test_forwards_null_sentinel(self, respx_mock: respx.Router) -> None:
        route = respx_mock.get(f"{BASE}/api/elements").mock(
            return_value=httpx.Response(
                200, json={"items": [], "total": 0, "page": 1, "page_size": 50},
            ),
        )
        async with IrisClient(BASE) as c:
            await tools._list_elements(c, {"package_id": "null"})
        assert "package_id=null" in str(route.calls[0].request.url)


class TestListPackageElements:
    @pytest.mark.anyio
    async def test_lists_via_package_endpoint(
        self, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get(f"{BASE}/api/packages/p1/elements").mock(
            return_value=httpx.Response(
                200, json={
                    "items": [_element(id="e1", package_id="p1")],
                    "total": 1, "page": 1, "page_size": 50,
                },
            ),
        )
        async with IrisClient(BASE) as c:
            result = await tools._list_package_elements(c, {"package_id": "p1"})
        assert route.called
        assert "e1" in result
