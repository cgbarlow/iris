"""MCP update_* tool tests (ADR-178, v6.3.0).

Covers tool inventory, happy-path field merging via the GET-then-PUT
helper, auth_required mapping on 401, and the special case for
update_set (collection_id must NOT be in its input schema — that's a
move_set concern).
"""

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
        "name": "Existing Name",
        "description": "Old desc",
        "created_at": "2026-05-12T00:00:00+00:00",
        "updated_at": "2026-05-12T00:00:00+00:00",
    }
    base.update(overrides)
    return base


class TestInventory:
    def test_all_update_tools_registered(self) -> None:
        names = {t.name for t in tools.tool_definitions()}
        assert {
            "update_collection",
            "update_set",
            "update_package",
            "update_diagram",
            "update_element",
        } <= names

    def test_update_set_schema_excludes_collection_id(self) -> None:
        """collection_id is a move concern, not a metadata edit."""
        defs = {t.name: t for t in tools.tool_definitions()}
        props = defs["update_set"].inputSchema["properties"]
        assert "collection_id" not in props, (
            "collection_id must not appear on update_set — use move_set"
        )


class TestUpdateCollection:
    @pytest.mark.asyncio
    async def test_partial_update_merges_with_current(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        # The handler does GET-then-PUT.
        respx_mock.get(f"{BASE}/api/collections/c-1").mock(
            return_value=httpx.Response(200, json=_entity(
                id="c-1", name="Collection One",
                description="orig desc",
            )),
        )
        put_route = respx_mock.put(f"{BASE}/api/collections/c-1").mock(
            return_value=httpx.Response(200, json=_entity(
                id="c-1", name="Collection One",
                description="new desc",
            )),
        )
        result = await tools.dispatch(
            "update_collection", client,
            {"collection_id": "c-1", "description": "new desc"},
        )
        body = json.loads(result[0].text)
        assert body["description"] == "new desc"
        # Verify PUT body preserved name from GET and applied the
        # description override.
        put_body = json.loads(put_route.calls[0].request.content)
        assert put_body["name"] == "Collection One"
        assert put_body["description"] == "new desc"

    @pytest.mark.asyncio
    async def test_401_returns_auth_required(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/collections/c-1").mock(
            return_value=httpx.Response(200, json=_entity(id="c-1")),
        )
        respx_mock.put(f"{BASE}/api/collections/c-1").mock(
            return_value=httpx.Response(401, json={"detail": "no auth"}),
        )
        result = await tools.dispatch(
            "update_collection", client,
            {"collection_id": "c-1", "name": "X"},
        )
        body = json.loads(result[0].text)
        assert body["success"] is False
        assert body["error"] == "auth_required"


class TestUpdateSet:
    @pytest.mark.asyncio
    async def test_update_set_preserves_collection_id(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        """Calling update_set with new name shouldn't strip the
        existing collection_id (handler preserves all SET_METADATA_FIELDS)."""
        respx_mock.get(f"{BASE}/api/sets/s-1").mock(
            return_value=httpx.Response(200, json=_entity(
                id="s-1", name="My Set",
                description="desc",
                collection_id="col-7",
            )),
        )
        put_route = respx_mock.put(f"{BASE}/api/sets/s-1").mock(
            return_value=httpx.Response(200, json=_entity(
                id="s-1", name="Renamed Set", collection_id="col-7",
            )),
        )
        await tools.dispatch(
            "update_set", client,
            {"set_id": "s-1", "name": "Renamed Set"},
        )
        put_body = json.loads(put_route.calls[0].request.content)
        # collection_id is intentionally NOT in the merge field list
        # for update_set (move_set's job), so it shouldn't appear in
        # the PUT body.
        assert "collection_id" not in put_body


class TestUpdatePackage:
    @pytest.mark.asyncio
    async def test_happy(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/packages/p-1").mock(
            return_value=httpx.Response(200, json=_entity(id="p-1")),
        )
        respx_mock.put(f"{BASE}/api/packages/p-1").mock(
            return_value=httpx.Response(200, json=_entity(
                id="p-1", description="updated",
            )),
        )
        result = await tools.dispatch(
            "update_package", client,
            {"package_id": "p-1", "description": "updated"},
        )
        body = json.loads(result[0].text)
        assert body["description"] == "updated"


class TestUpdateDiagram:
    @pytest.mark.asyncio
    async def test_data_replace_merges_with_current_name(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/diagrams/d-1").mock(
            return_value=httpx.Response(200, json=_entity(
                id="d-1", name="Old Diagram Name",
                data={"nodes": [], "edges": []},
            )),
        )
        put_route = respx_mock.put(f"{BASE}/api/diagrams/d-1").mock(
            return_value=httpx.Response(200, json=_entity(
                id="d-1", name="Old Diagram Name",
                data={"nodes": [{"id": "n1"}], "edges": []},
            )),
        )
        await tools.dispatch(
            "update_diagram", client,
            {
                "diagram_id": "d-1",
                "data": {"nodes": [{"id": "n1"}], "edges": []},
            },
        )
        put_body = json.loads(put_route.calls[0].request.content)
        assert put_body["name"] == "Old Diagram Name"
        assert put_body["data"] == {"nodes": [{"id": "n1"}], "edges": []}


class TestUpdateElement:
    @pytest.mark.asyncio
    async def test_happy(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/elements/el-1").mock(
            return_value=httpx.Response(200, json=_entity(id="el-1")),
        )
        respx_mock.put(f"{BASE}/api/elements/el-1").mock(
            return_value=httpx.Response(200, json=_entity(
                id="el-1", description="el desc",
            )),
        )
        result = await tools.dispatch(
            "update_element", client,
            {"element_id": "el-1", "description": "el desc"},
        )
        body = json.loads(result[0].text)
        assert body["description"] == "el desc"


class TestIfMatchHeader:
    """Versioned update endpoints (elements / diagrams / packages)
    require an ``If-Match`` header — backend returns HTTP 428 without
    it. Regression guard for v6.7.3 / issue #158."""

    @pytest.mark.asyncio
    async def test_update_element_sends_if_match(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/elements/el-1").mock(
            return_value=httpx.Response(
                200, json=_entity(id="el-1", current_version=7),
            ),
        )
        put_route = respx_mock.put(f"{BASE}/api/elements/el-1").mock(
            return_value=httpx.Response(200, json=_entity(id="el-1")),
        )
        await tools.dispatch(
            "update_element", client,
            {"element_id": "el-1", "description": "x"},
        )
        assert put_route.calls[0].request.headers.get("If-Match") == "7"

    @pytest.mark.asyncio
    async def test_update_element_package_id_sends_if_match(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        """The package_id special-case path takes a different branch
        than the standard helper — it must also send If-Match."""
        respx_mock.get(f"{BASE}/api/elements/el-2").mock(
            return_value=httpx.Response(
                200, json=_entity(id="el-2", current_version=3),
            ),
        )
        put_route = respx_mock.put(f"{BASE}/api/elements/el-2").mock(
            return_value=httpx.Response(200, json=_entity(id="el-2")),
        )
        await tools.dispatch(
            "update_element", client,
            {"element_id": "el-2", "package_id": "pkg-a"},
        )
        assert put_route.calls[0].request.headers.get("If-Match") == "3"

    @pytest.mark.asyncio
    async def test_update_diagram_sends_if_match(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/diagrams/d-1").mock(
            return_value=httpx.Response(
                200, json=_entity(id="d-1", current_version=4),
            ),
        )
        put_route = respx_mock.put(f"{BASE}/api/diagrams/d-1").mock(
            return_value=httpx.Response(200, json=_entity(id="d-1")),
        )
        await tools.dispatch(
            "update_diagram", client,
            {"diagram_id": "d-1", "description": "x"},
        )
        assert put_route.calls[0].request.headers.get("If-Match") == "4"

    @pytest.mark.asyncio
    async def test_update_package_sends_if_match(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/packages/pk-1").mock(
            return_value=httpx.Response(
                200, json=_entity(id="pk-1", current_version=2),
            ),
        )
        put_route = respx_mock.put(f"{BASE}/api/packages/pk-1").mock(
            return_value=httpx.Response(200, json=_entity(id="pk-1")),
        )
        await tools.dispatch(
            "update_package", client,
            {"package_id": "pk-1", "description": "x"},
        )
        assert put_route.calls[0].request.headers.get("If-Match") == "2"

    @pytest.mark.asyncio
    async def test_update_set_omits_if_match(
        self, client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        """Unversioned endpoints (sets, collections) don't include
        ``current_version`` in their GET response — no If-Match header
        should be sent (backend would 400 on a stray header anyway)."""
        respx_mock.get(f"{BASE}/api/sets/s-1").mock(
            return_value=httpx.Response(200, json=_entity(id="s-1")),
        )
        put_route = respx_mock.put(f"{BASE}/api/sets/s-1").mock(
            return_value=httpx.Response(200, json=_entity(id="s-1")),
        )
        await tools.dispatch(
            "update_set", client,
            {"set_id": "s-1", "description": "x"},
        )
        assert "If-Match" not in put_route.calls[0].request.headers
