"""MCP ``patch_diagram`` tool (ADR-252, SPEC-252-A, v6.51.0, issue #301).

Small edits to large diagrams without resending the canvas: an ordered,
atomic list of node / edge operations plus ``sync_labels``, with optional
``expected_version`` optimistic concurrency.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from iris_client import IrisClient

from iris_mcp import tools

BASE = "http://iris.test"
WEB = "https://iris.example"
OPS = [{"op": "remove_edge", "id": "x1"}, {"op": "sync_labels"}]
RESULT = {
    "id": "d-1", "current_version": 5, "updated_at": "2026", "applied": 2,
    "results": [{"index": 0, "op": "remove_edge", "id": "x1"},
                {"index": 1, "op": "sync_labels", "ids": ["n1"], "skipped": []}],
}


def _defs() -> dict[str, object]:
    return {t.name: t for t in tools.tool_definitions()}


class TestInventory:
    def test_registered_with_schema(self) -> None:
        schema = _defs()["patch_diagram"].inputSchema
        assert schema["required"] == ["diagram_id", "operations"]
        ops = schema["properties"]["operations"]
        assert ops["minItems"] == 1
        assert ops["maxItems"] == 200
        kinds = ops["items"]["properties"]["op"]["enum"]
        assert set(kinds) == {
            "add_node", "update_node", "remove_node", "add_edge",
            "update_edge", "remove_edge", "sync_labels",
        }
        for field in ("expected_version", "change_summary"):
            assert field in schema["properties"]
        assert schema["properties"]["expected_version"]["type"] == "integer"

    def test_description_explains_ops_and_atomicity(self) -> None:
        desc = _defs()["patch_diagram"].description
        for word in ("atomic", "expected_version", "sync_labels", "cascade_edges",
                     "relationshipId", "update_diagram"):
            assert word in desc

    def test_update_diagram_points_at_patch_diagram(self) -> None:
        assert "patch_diagram" in _defs()["update_diagram"].description

    def test_server_instructions_point_at_patch_diagram(self) -> None:
        from iris_mcp.server_instructions import _FALLBACK_INSTRUCTIONS

        assert "`patch_diagram`" in _FALLBACK_INSTRUCTIONS


class TestPatchDiagram:
    @pytest.mark.anyio
    async def test_forwards_ops_and_decorates_web_url(
        self, respx_mock: respx.Router, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("IRIS_WEB_URL", WEB)
        route = respx_mock.patch(f"{BASE}/api/diagrams/d-1").mock(
            return_value=httpx.Response(200, json=RESULT),
        )
        async with IrisClient(BASE, token="t") as c:
            out = await tools._patch_diagram(c, {
                "diagram_id": "d-1", "operations": OPS,
                "expected_version": 4, "change_summary": "tidy",
            })
        req = route.calls[0].request
        assert req.headers["If-Match"] == "4"
        assert json.loads(req.content) == {"operations": OPS, "change_summary": "tidy"}
        payload = json.loads(out)
        assert payload["current_version"] == 5
        assert payload["results"] == RESULT["results"]
        assert payload["web_url"] == f"{WEB}/views/d-1"

    @pytest.mark.anyio
    async def test_without_expected_version(self, respx_mock: respx.Router) -> None:
        route = respx_mock.patch(f"{BASE}/api/diagrams/d-1").mock(
            return_value=httpx.Response(200, json=RESULT),
        )
        async with IrisClient(BASE, token="t") as c:
            await tools._patch_diagram(c, {"diagram_id": "d-1", "operations": OPS})
        assert "If-Match" not in route.calls[0].request.headers

    @pytest.mark.anyio
    async def test_version_conflict_is_structured(self, respx_mock: respx.Router) -> None:
        detail = {"error": "version_conflict", "current_version": 9,
                  "expected_version": 4, "message": "diagram is at version 9, not 4"}
        respx_mock.patch(f"{BASE}/api/diagrams/d-1").mock(
            return_value=httpx.Response(409, json={"detail": detail}),
        )
        async with IrisClient(BASE, token="t") as c:
            out = await tools._patch_diagram(c, {
                "diagram_id": "d-1", "operations": OPS, "expected_version": 4,
            })
        payload = json.loads(out)
        assert payload["success"] is False
        assert payload["error"] == "version_conflict"
        assert payload["current_version"] == 9

    @pytest.mark.anyio
    async def test_failed_op_is_structured(self, respx_mock: respx.Router) -> None:
        detail = {"error": "operation_failed", "op_index": 0, "op": "remove_edge",
                  "message": "operations[0] (remove_edge): edge 'x1' does not exist"}
        respx_mock.patch(f"{BASE}/api/diagrams/d-1").mock(
            return_value=httpx.Response(422, json={"detail": detail}),
        )
        async with IrisClient(BASE, token="t") as c:
            out = await tools._patch_diagram(c, {"diagram_id": "d-1", "operations": OPS})
        payload = json.loads(out)
        assert payload["success"] is False
        assert payload["op_index"] == 0
        assert "does not exist" in payload["message"]

    @pytest.mark.anyio
    async def test_other_http_errors_propagate(self, respx_mock: respx.Router) -> None:
        respx_mock.patch(f"{BASE}/api/diagrams/d-1").mock(
            return_value=httpx.Response(404, json={"detail": "Diagram not found"}),
        )
        async with IrisClient(BASE, token="t") as c:
            out = await tools.dispatch(
                "patch_diagram", c, {"diagram_id": "d-1", "operations": OPS},
            )
        assert out[0].text.startswith("ERROR: HTTP 404")

    @pytest.mark.anyio
    async def test_auth_required_payload(self, respx_mock: respx.Router) -> None:
        respx_mock.patch(f"{BASE}/api/diagrams/d-1").mock(
            return_value=httpx.Response(401, json={"detail": "Not authenticated"}),
        )
        async with IrisClient(BASE) as c:
            out = await tools._patch_diagram(c, {"diagram_id": "d-1", "operations": OPS})
        assert json.loads(out)["error"] == "auth_required"
