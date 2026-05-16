"""MCP move_* tool tests (ADR-178, v6.3.0)."""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from iris_client import IrisClient

from iris_mcp import tools

BASE = "http://iris.test"


def _entity(**overrides):
    base = {
        "id": "e-1",
        "name": "Existing",
        "description": None,
        "created_at": "2026-05-12T00:00:00+00:00",
        "updated_at": "2026-05-12T00:00:00+00:00",
    }
    base.update(overrides)
    return base


class TestInventory:
    def test_all_move_tools_registered(self) -> None:
        names = {t.name for t in tools.tool_definitions()}
        assert {"move_diagram", "move_package", "move_set"} <= names


class TestMoveDiagram:
    @pytest.mark.asyncio
    async def test_to_specific_package(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        put_route = respx_mock.put(f"{BASE}/api/diagrams/d-1/parent").mock(
            return_value=httpx.Response(200, json={
                "id": "d-1", "parent_package_id": "pkg-7",
            }),
        )
        result = await tools.dispatch(
            "move_diagram", client,
            {"diagram_id": "d-1", "parent_package_id": "pkg-7"},
        )
        body = json.loads(result[0].text)
        assert body["parent_package_id"] == "pkg-7"
        put_body = json.loads(put_route.calls[0].request.content)
        assert put_body == {"parent_package_id": "pkg-7"}

    @pytest.mark.asyncio
    async def test_to_root(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        put_route = respx_mock.put(f"{BASE}/api/diagrams/d-1/parent").mock(
            return_value=httpx.Response(200, json={
                "id": "d-1", "parent_package_id": None,
            }),
        )
        await tools.dispatch(
            "move_diagram", client,
            {"diagram_id": "d-1", "parent_package_id": None},
        )
        put_body = json.loads(put_route.calls[0].request.content)
        assert put_body == {"parent_package_id": None}

    @pytest.mark.asyncio
    async def test_401_returns_auth_required(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.put(f"{BASE}/api/diagrams/d-1/parent").mock(
            return_value=httpx.Response(401, json={"detail": "x"}),
        )
        result = await tools.dispatch(
            "move_diagram", client,
            {"diagram_id": "d-1", "parent_package_id": "pkg-7"},
        )
        body = json.loads(result[0].text)
        assert body["error"] == "auth_required"


class TestMovePackage:
    @pytest.mark.asyncio
    async def test_to_specific_parent(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        put_route = respx_mock.put(f"{BASE}/api/packages/p-1/parent").mock(
            return_value=httpx.Response(200, json={
                "id": "p-1", "parent_package_id": "pkg-parent",
            }),
        )
        await tools.dispatch(
            "move_package", client,
            {"package_id": "p-1", "parent_package_id": "pkg-parent"},
        )
        put_body = json.loads(put_route.calls[0].request.content)
        assert put_body == {"parent_package_id": "pkg-parent"}

    @pytest.mark.asyncio
    async def test_to_root(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        put_route = respx_mock.put(f"{BASE}/api/packages/p-1/parent").mock(
            return_value=httpx.Response(200, json={
                "id": "p-1", "parent_package_id": None,
            }),
        )
        await tools.dispatch(
            "move_package", client,
            {"package_id": "p-1", "parent_package_id": None},
        )
        put_body = json.loads(put_route.calls[0].request.content)
        assert put_body == {"parent_package_id": None}


class TestMoveSet:
    @pytest.mark.asyncio
    async def test_to_different_collection_preserves_metadata(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/sets/s-1").mock(
            return_value=httpx.Response(200, json=_entity(
                id="s-1", name="My Set", description="d",
                collection_id="col-old",
                system_prompt="sp",
            )),
        )
        put_route = respx_mock.put(f"{BASE}/api/sets/s-1").mock(
            return_value=httpx.Response(200, json=_entity(
                id="s-1", name="My Set", description="d",
                collection_id="col-new",
            )),
        )
        result = await tools.dispatch(
            "move_set", client,
            {"set_id": "s-1", "collection_id": "col-new"},
        )
        body = json.loads(result[0].text)
        assert body["collection_id"] == "col-new"
        put_body = json.loads(put_route.calls[0].request.content)
        # Move must include the new collection_id…
        assert put_body["collection_id"] == "col-new"
        # …and preserve other metadata fields from the GET.
        assert put_body["name"] == "My Set"
        assert put_body["description"] == "d"
        assert put_body["system_prompt"] == "sp"

    @pytest.mark.asyncio
    async def test_uncollect_with_null_collection_id(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/sets/s-1").mock(
            return_value=httpx.Response(200, json=_entity(
                id="s-1", collection_id="col-old",
            )),
        )
        put_route = respx_mock.put(f"{BASE}/api/sets/s-1").mock(
            return_value=httpx.Response(200, json=_entity(
                id="s-1", collection_id=None,
            )),
        )
        await tools.dispatch(
            "move_set", client,
            {"set_id": "s-1", "collection_id": None},
        )
        put_body = json.loads(put_route.calls[0].request.content)
        # Critical: null collection_id is preserved in the PUT body —
        # this is the "un-group" semantics. The partial-merge helper
        # used for update_set would drop None overrides; move_set has
        # to special-case this.
        assert "collection_id" in put_body
        assert put_body["collection_id"] is None
