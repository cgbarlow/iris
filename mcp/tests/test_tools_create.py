"""MCP create_* tool tests (ADR-161, SPEC-161-A).

Covers create_collection, create_set, create_package — happy paths,
auth_required mapping on 401, presence of the destination-confirmation
preamble in every write tool's description, and presence of the new
tools in the tool inventory.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from iris_client import IrisClient

from iris_mcp import tools

BASE = "http://iris.test"


def _entity_payload(**overrides: object) -> dict[str, object]:
    """Minimal payload that satisfies the iris-client EntityBase model."""
    base = {
        "id": "e-1",
        "name": "Whatever",
        "description": None,
        "created_at": "2026-05-12T00:00:00+00:00",
        "updated_at": "2026-05-12T00:00:00+00:00",
    }
    base.update(overrides)
    return base


class TestInventory:
    def test_new_tools_registered(self) -> None:
        names = {t.name for t in tools.tool_definitions()}
        assert {"create_collection", "create_set", "create_package"} <= names

    def test_new_tools_have_name_property_in_schema(self) -> None:
        defs = {t.name: t for t in tools.tool_definitions()}
        for tool_name in ("create_collection", "create_set", "create_package"):
            props = defs[tool_name].inputSchema["properties"]
            assert "name" in props
            assert defs[tool_name].inputSchema["required"] == ["name"]


class TestDestinationPreamble:
    def test_preamble_in_save_doview_analysis_description(self) -> None:
        defs = {t.name: t for t in tools.tool_definitions()}
        assert "BEFORE CALLING, confirm with the user" in defs[
            "save_doview_analysis"
        ].description

    def test_preamble_in_each_create_tool_description(self) -> None:
        defs = {t.name: t for t in tools.tool_definitions()}
        for tool_name in ("create_collection", "create_set", "create_package"):
            assert "BEFORE CALLING, confirm with the user" in defs[
                tool_name
            ].description, f"preamble missing from {tool_name}"


class TestCreateCollection:
    @pytest.mark.asyncio
    async def test_happy_path(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(f"{BASE}/api/collections").mock(
            return_value=httpx.Response(
                201,
                json=_entity_payload(id="col-1", name="Outcomes Work"),
            ),
        )
        result = await tools.dispatch(
            "create_collection", client,
            {"name": "Outcomes Work"},
        )
        body = json.loads(result[0].text)
        assert body["id"] == "col-1"
        assert body["name"] == "Outcomes Work"

    @pytest.mark.asyncio
    async def test_401_returns_auth_required_payload(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(f"{BASE}/api/collections").mock(
            return_value=httpx.Response(401, json={"detail": "no auth"}),
        )
        result = await tools.dispatch(
            "create_collection", client, {"name": "X"},
        )
        body = json.loads(result[0].text)
        assert body["success"] is False
        assert body["error"] == "auth_required"
        assert body["next_tool"] == "iris_authenticate"
        assert "/settings/mcp-pairing" in body["pairing_url"]


class TestCreateSet:
    @pytest.mark.asyncio
    async def test_happy_path_with_collection_id(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.post(f"{BASE}/api/sets").mock(
            return_value=httpx.Response(
                201,
                json={
                    **_entity_payload(id="set-1", name="Pilot DoView"),
                    "collection_id": "col-1",
                },
            ),
        )
        result = await tools.dispatch(
            "create_set", client,
            {"name": "Pilot DoView", "collection_id": "col-1"},
        )
        body = json.loads(result[0].text)
        assert body["id"] == "set-1"
        sent = route.calls.last.request.content.decode()
        assert '"collection_id":"col-1"' in sent

    @pytest.mark.asyncio
    async def test_401_returns_auth_required_payload(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(f"{BASE}/api/sets").mock(
            return_value=httpx.Response(401, json={"detail": "no auth"}),
        )
        result = await tools.dispatch(
            "create_set", client, {"name": "X"},
        )
        body = json.loads(result[0].text)
        assert body["success"] is False
        assert body["error"] == "auth_required"


class TestCreatePackage:
    @pytest.mark.asyncio
    async def test_happy_path_with_set_and_parent(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.post(f"{BASE}/api/packages").mock(
            return_value=httpx.Response(
                201,
                json={
                    **_entity_payload(id="pkg-1", name="Section A"),
                    "set_id": "set-1",
                    "parent_package_id": "pkg-root",
                    "current_version": 1,
                    "metadata": {"order": 1},
                },
            ),
        )
        result = await tools.dispatch(
            "create_package", client,
            {
                "name": "Section A",
                "set_id": "set-1",
                "parent_package_id": "pkg-root",
                "metadata": {"order": 1},
            },
        )
        body = json.loads(result[0].text)
        assert body["id"] == "pkg-1"
        sent = route.calls.last.request.content.decode()
        assert '"set_id":"set-1"' in sent
        assert '"parent_package_id":"pkg-root"' in sent

    @pytest.mark.asyncio
    async def test_401_returns_auth_required_payload(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(f"{BASE}/api/packages").mock(
            return_value=httpx.Response(401, json={"detail": "no auth"}),
        )
        result = await tools.dispatch(
            "create_package", client, {"name": "X"},
        )
        body = json.loads(result[0].text)
        assert body["success"] is False
        assert body["error"] == "auth_required"
