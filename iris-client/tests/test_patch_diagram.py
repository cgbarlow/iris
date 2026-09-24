"""iris-client ``patch_diagram`` (ADR-252, SPEC-252-A, v6.51.0, #301).

Shared by the MCP ``patch_diagram`` tool and ``iris patch diagram``.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from iris_client import IrisClient
from iris_client.exceptions import IrisAuthError, IrisHTTPError

BASE = "http://iris.test"
OPS = [
    {"op": "add_node", "node": {"id": "n9", "position": {"x": 0, "y": 0},
                                "data": {"label": "N", "entityType": "object"}}},
    {"op": "sync_labels"},
]
RESULT = {
    "id": "d-1", "current_version": 8, "updated_at": "2026", "applied": 2,
    "results": [{"index": 0, "op": "add_node", "id": "n9"},
                {"index": 1, "op": "sync_labels", "ids": [], "skipped": []}],
}


class TestPatchDiagram:
    @pytest.mark.asyncio
    async def test_sends_operations_with_if_match(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.patch(f"{BASE}/api/diagrams/d-1").mock(
            return_value=httpx.Response(200, json=RESULT),
        )
        result = await pat_client.patch_diagram(
            "d-1", OPS, expected_version=7, change_summary="Add N",
        )
        assert result == RESULT
        request = route.calls.last.request
        assert request.headers["If-Match"] == "7"
        assert json.loads(request.content) == {
            "operations": OPS, "change_summary": "Add N",
        }

    @pytest.mark.asyncio
    async def test_no_expected_version_sends_no_if_match(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.patch(f"{BASE}/api/diagrams/d-1").mock(
            return_value=httpx.Response(200, json=RESULT),
        )
        await pat_client.patch_diagram("d-1", OPS)
        request = route.calls.last.request
        assert "If-Match" not in request.headers
        assert json.loads(request.content) == {"operations": OPS}

    @pytest.mark.asyncio
    async def test_structured_error_message_is_readable(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        detail = {"error": "operation_failed", "op_index": 1, "op": "remove_edge",
                  "message": "operations[1] (remove_edge): edge 'x' does not exist"}
        respx_mock.patch(f"{BASE}/api/diagrams/d-1").mock(
            return_value=httpx.Response(422, json={"detail": detail}),
        )
        with pytest.raises(IrisHTTPError) as info:
            await pat_client.patch_diagram("d-1", OPS)
        assert info.value.status_code == 422
        assert info.value.detail == detail["message"]
        assert info.value.response is not None
        assert info.value.response.json()["detail"]["op_index"] == 1

    @pytest.mark.asyncio
    async def test_auth_error_raises(
        self, anon_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.patch(f"{BASE}/api/diagrams/d-1").mock(
            return_value=httpx.Response(401, json={"detail": "nope"}),
        )
        with pytest.raises(IrisAuthError):
            await anon_client.patch_diagram("d-1", OPS)
