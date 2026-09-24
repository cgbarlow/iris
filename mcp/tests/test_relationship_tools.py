"""MCP relationship tools (ADR-249, SPEC-249-A, v6.50.0, issue #298).

- create_relationships — batch (<=100), per-item isolation, role fields.
- update_relationship — partial update; reads the current version for
  If-Match; relationship_type / roles / label / data.
- list_relationships — element_id (both directions) or set_id, optional
  relationship_type, pagination; items carry roles + data.
- get_relationship — one relationship.
- delete_relationship — soft delete.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from iris_client import IrisClient

from iris_mcp import tools

BASE = "http://iris.test"


def _rel(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "r-1", "source_element_id": "a", "target_element_id": "b",
        "relationship_type": "association", "current_version": 2,
        "label": None, "description": None,
        "data": {"sourceRole": "partner"},
        "source_role": "partner", "target_role": None,
        "created_at": "2026", "created_by": "u", "updated_at": "2026",
        "is_deleted": False,
        "source_element_name": "A", "target_element_name": "B",
    }
    base.update(overrides)
    return base


def _defs() -> dict[str, object]:
    return {t.name: t for t in tools.tool_definitions()}


class TestInventory:
    def test_tools_registered(self) -> None:
        names = set(_defs())
        assert {
            "create_relationships", "update_relationship",
            "list_relationships", "get_relationship", "delete_relationship",
        } <= names

    def test_create_schema(self) -> None:
        schema = _defs()["create_relationships"].inputSchema
        assert schema["required"] == ["relationships"]
        arr = schema["properties"]["relationships"]
        assert arr["minItems"] == 1
        assert arr["maxItems"] == 100
        item = arr["items"]
        assert set(item["required"]) == {
            "source_element_id", "target_element_id", "relationship_type",
        }
        for field in ("source_role", "target_role", "label", "description", "data"):
            assert field in item["properties"]

    def test_update_schema(self) -> None:
        schema = _defs()["update_relationship"].inputSchema
        assert schema["required"] == ["relationship_id"]
        for field in (
            "relationship_type", "source_role", "target_role",
            "label", "description", "data", "change_summary",
        ):
            assert field in schema["properties"]

    def test_list_schema(self) -> None:
        props = _defs()["list_relationships"].inputSchema["properties"]
        for field in ("element_id", "set_id", "relationship_type", "page", "page_size"):
            assert field in props

    def test_server_instructions_point_at_relationship_tools(self) -> None:
        from iris_mcp.server_instructions import _FALLBACK_INSTRUCTIONS

        for name in (
            "list_relationships", "create_relationships",
            "update_relationship", "delete_relationship",
        ):
            assert f"`{name}`" in _FALLBACK_INSTRUCTIONS
        assert "data.relationshipId" in _FALLBACK_INSTRUCTIONS

    def test_server_instructions_do_not_carve_out_relationship_reads(self) -> None:
        """ADR-251: relationship reads are anonymous like every other read,
        so AUTH RECOVERY keeps the plain "reads work without sign-in" line."""
        from iris_mcp.server_instructions import _FALLBACK_INSTRUCTIONS

        assert "except `list_relationships`" not in _FALLBACK_INSTRUCTIONS
        assert "work without sign-in; only writes" in _FALLBACK_INSTRUCTIONS

    def test_read_tool_descriptions_do_not_claim_sign_in(self) -> None:
        for name in ("list_relationships", "get_relationship"):
            assert "sign-in" not in _defs()[name].description.lower()

    def test_create_description_mentions_diagram_edge_reuse(self) -> None:
        desc = _defs()["create_relationships"].description
        assert "relationshipId" in desc
        assert "update_diagram" in desc
        # Edge direction must be spelled out (reviewer finding, ADR-249).
        assert "edge's source node" in desc


class TestCreateRelationships:
    @pytest.mark.anyio
    async def test_forwards_items_and_returns_envelope(
        self, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.post(f"{BASE}/api/batch/relationships/create").mock(
            return_value=httpx.Response(200, json={
                "succeeded": 1, "failed": 1,
                "errors": ["Relationship at index 1: cross-set relationships are not allowed"],
                "ids": ["r-1"],
            }),
        )
        items = [
            {"source_element_id": "a", "target_element_id": "b",
             "relationship_type": "association", "source_role": "partner"},
            {"source_element_id": "a", "target_element_id": "x",
             "relationship_type": "association"},
        ]
        async with IrisClient(BASE) as c:
            out = await tools._create_relationships(c, {"relationships": items})
        assert json.loads(route.calls[0].request.content) == {"relationships": items}
        payload = json.loads(out)
        assert payload["succeeded"] == 1
        assert payload["ids"] == ["r-1"]
        assert "cross-set" in payload["errors"][0]

    @pytest.mark.anyio
    async def test_auth_required_payload(self, respx_mock: respx.Router) -> None:
        respx_mock.post(f"{BASE}/api/batch/relationships/create").mock(
            return_value=httpx.Response(401, json={"detail": "Not authenticated"}),
        )
        async with IrisClient(BASE) as c:
            out = await tools._create_relationships(c, {"relationships": [{}]})
        assert json.loads(out)["error"] == "auth_required"


class TestUpdateRelationship:
    @pytest.mark.anyio
    async def test_partial_update_with_if_match(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/relationships/r-1").mock(
            return_value=httpx.Response(200, json=_rel()),
        )
        put = respx_mock.put(f"{BASE}/api/relationships/r-1").mock(
            return_value=httpx.Response(200, json=_rel(
                relationship_type="composition", current_version=3,
                data={"sourceRole": "partner", "targetRole": "child"},
                target_role="child",
            )),
        )
        async with IrisClient(BASE) as c:
            out = await tools._update_relationship(c, {
                "relationship_id": "r-1",
                "relationship_type": "composition",
                "target_role": "child",
            })
        req = put.calls[0].request
        assert req.headers["If-Match"] == "2"
        body = json.loads(req.content)
        assert body["relationship_type"] == "composition"
        assert body["target_role"] == "child"
        assert body["data"] == {"sourceRole": "partner"}
        assert json.loads(out)["target_role"] == "child"

    @pytest.mark.anyio
    async def test_auth_required_payload(self, respx_mock: respx.Router) -> None:
        respx_mock.get(f"{BASE}/api/relationships/r-1").mock(
            return_value=httpx.Response(401, json={"detail": "Not authenticated"}),
        )
        async with IrisClient(BASE) as c:
            out = await tools._update_relationship(c, {"relationship_id": "r-1"})
        assert json.loads(out)["error"] == "auth_required"


class TestListGetDelete:
    @pytest.mark.anyio
    async def test_list_forwards_filters(self, respx_mock: respx.Router) -> None:
        route = respx_mock.get(f"{BASE}/api/relationships").mock(
            return_value=httpx.Response(200, json={
                "items": [_rel()], "total": 1, "page": 1, "page_size": 100,
            }),
        )
        async with IrisClient(BASE) as c:
            out = await tools._list_relationships(c, {
                "set_id": "s-1", "relationship_type": "association",
                "page": 1, "page_size": 100,
            })
        params = route.calls[0].request.url.params
        assert params["set_id"] == "s-1"
        assert params["relationship_type"] == "association"
        assert params["page_size"] == "100"
        payload = json.loads(out)
        assert payload["total"] == 1
        assert payload["items"][0]["source_role"] == "partner"
        assert payload["items"][0]["data"] == {"sourceRole": "partner"}

    @pytest.mark.anyio
    async def test_list_by_element(self, respx_mock: respx.Router) -> None:
        route = respx_mock.get(f"{BASE}/api/relationships").mock(
            return_value=httpx.Response(200, json={
                "items": [], "total": 0, "page": 1, "page_size": 50,
            }),
        )
        async with IrisClient(BASE) as c:
            await tools._list_relationships(c, {"element_id": "el-1"})
        assert route.calls[0].request.url.params["element_id"] == "el-1"

    @pytest.mark.anyio
    async def test_list_requires_a_scope(self) -> None:
        async with IrisClient(BASE) as c:
            out = await tools._list_relationships(c, {})
        payload = json.loads(out)
        assert payload["success"] is False
        assert "element_id" in payload["message"]

    @pytest.mark.anyio
    async def test_get(self, respx_mock: respx.Router) -> None:
        respx_mock.get(f"{BASE}/api/relationships/r-1").mock(
            return_value=httpx.Response(200, json=_rel()),
        )
        async with IrisClient(BASE) as c:
            out = await tools._get_relationship(c, {"relationship_id": "r-1"})
        assert json.loads(out)["id"] == "r-1"

    @pytest.mark.anyio
    async def test_delete(self, respx_mock: respx.Router) -> None:
        respx_mock.get(f"{BASE}/api/relationships/r-1").mock(
            return_value=httpx.Response(200, json=_rel()),
        )
        delete = respx_mock.delete(f"{BASE}/api/relationships/r-1").mock(
            return_value=httpx.Response(204),
        )
        async with IrisClient(BASE) as c:
            out = await tools._delete_relationship(c, {"relationship_id": "r-1"})
        assert delete.calls[0].request.headers["If-Match"] == "2"
        assert json.loads(out) == {
            "success": True, "relationship_id": "r-1", "deleted": True,
        }

    @pytest.mark.anyio
    async def test_dispatch_surfaces_http_errors(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/relationships/nope").mock(
            return_value=httpx.Response(404, json={"detail": "Relationship not found"}),
        )
        async with IrisClient(BASE) as c:
            out = await tools.dispatch("delete_relationship", c, {"relationship_id": "nope"})
        assert out[0].text.startswith("ERROR:")
        assert "not found" in out[0].text.lower()
