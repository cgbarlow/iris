"""iris-client relationship methods (ADR-249, SPEC-249-A, v6.50.0, #298).

Shared by iris-mcp (create_relationships / update_relationship /
list_relationships / get_relationship / delete_relationship) and iris-cli
(`iris create|update|delete relationship`, `iris relationships list|get`).
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from iris_client import IrisClient
from iris_client.exceptions import IrisAuthError, IrisHTTPError

BASE = "http://iris.test"


def _rel(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "r-1",
        "source_element_id": "a",
        "target_element_id": "b",
        "relationship_type": "association",
        "current_version": 3,
        "label": "L",
        "description": "D",
        "data": {"gedcom_role": "HUSB", "sourceRole": "partner"},
        "source_role": "partner",
        "target_role": None,
        "created_at": "2026", "created_by": "u", "updated_at": "2026",
        "is_deleted": False,
        "source_element_name": "A", "target_element_name": "B",
    }
    base.update(overrides)
    return base


class TestCreateRelationships:
    @pytest.mark.asyncio
    async def test_posts_batch_envelope(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.post(f"{BASE}/api/batch/relationships/create").mock(
            return_value=httpx.Response(200, json={
                "succeeded": 1, "failed": 0, "errors": [], "ids": ["r-1"],
            }),
        )
        items = [{
            "source_element_id": "a", "target_element_id": "b",
            "relationship_type": "association",
            "source_role": "partner", "target_role": "child",
            "data": {"child_order": 1},
        }]
        result = await pat_client.create_relationships(items)
        assert result["ids"] == ["r-1"]
        assert json.loads(route.calls.last.request.content) == {
            "relationships": items,
        }

    @pytest.mark.asyncio
    async def test_auth_error_raises(
        self, anon_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.post(f"{BASE}/api/batch/relationships/create").mock(
            return_value=httpx.Response(401, json={"detail": "nope"}),
        )
        with pytest.raises(IrisAuthError):
            await anon_client.create_relationships([{"source_element_id": "a"}])


class TestListAndGet:
    @pytest.mark.asyncio
    async def test_list_forwards_filters_and_returns_envelope(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get(f"{BASE}/api/relationships").mock(
            return_value=httpx.Response(200, json={
                "items": [_rel()], "total": 1, "page": 2, "page_size": 10,
            }),
        )
        result = await pat_client.list_relationships(
            set_id="s-1", relationship_type="association", page=2, page_size=10,
        )
        assert result["total"] == 1
        assert result["items"][0]["source_role"] == "partner"
        params = route.calls.last.request.url.params
        assert params["set_id"] == "s-1"
        assert params["relationship_type"] == "association"
        assert params["page"] == "2"
        assert params["page_size"] == "10"
        assert "element_id" not in params

    @pytest.mark.asyncio
    async def test_list_by_element(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get(f"{BASE}/api/relationships").mock(
            return_value=httpx.Response(200, json={
                "items": [], "total": 0, "page": 1, "page_size": 50,
            }),
        )
        await pat_client.list_relationships(element_id="el-1")
        assert route.calls.last.request.url.params["element_id"] == "el-1"

    @pytest.mark.asyncio
    async def test_get(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/relationships/r-1").mock(
            return_value=httpx.Response(200, json=_rel()),
        )
        rel = await pat_client.get_relationship("r-1")
        assert rel["id"] == "r-1"


class TestUpdateRelationship:
    @pytest.mark.asyncio
    async def test_partial_update_reads_version_and_merges(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/relationships/r-1").mock(
            return_value=httpx.Response(200, json=_rel()),
        )
        put = respx_mock.put(f"{BASE}/api/relationships/r-1").mock(
            return_value=httpx.Response(200, json=_rel(
                relationship_type="composition", current_version=4,
            )),
        )
        result = await pat_client.update_relationship(
            "r-1", relationship_type="composition", target_role="child",
        )
        assert result["relationship_type"] == "composition"
        req = put.calls.last.request
        assert req.headers["If-Match"] == "3"
        body = json.loads(req.content)
        assert body == {
            "label": "L",
            "description": "D",
            "data": {"gedcom_role": "HUSB", "sourceRole": "partner"},
            "relationship_type": "composition",
            "target_role": "child",
        }

    @pytest.mark.asyncio
    async def test_new_data_keeps_existing_roles(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        """`data` replaces the stored data, but role names live in data
        too — they're carried over unless source_role / target_role say
        otherwise, so fixing an attribute can't silently drop a role."""
        respx_mock.get(f"{BASE}/api/relationships/r-1").mock(
            return_value=httpx.Response(200, json=_rel()),
        )
        put = respx_mock.put(f"{BASE}/api/relationships/r-1").mock(
            return_value=httpx.Response(200, json=_rel()),
        )
        await pat_client.update_relationship("r-1", data={"gedcom_role": "WIFE"})
        body = json.loads(put.calls.last.request.content)
        assert body["data"] == {"gedcom_role": "WIFE", "sourceRole": "partner"}
        assert "source_role" not in body

    @pytest.mark.asyncio
    async def test_conflict_surfaces(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/relationships/r-1").mock(
            return_value=httpx.Response(200, json=_rel()),
        )
        respx_mock.put(f"{BASE}/api/relationships/r-1").mock(
            return_value=httpx.Response(409, json={"detail": "Version conflict"}),
        )
        with pytest.raises(IrisHTTPError) as exc_info:
            await pat_client.update_relationship("r-1", label="x")
        assert exc_info.value.status_code == 409


class TestDeleteRelationship:
    @pytest.mark.asyncio
    async def test_reads_version_then_deletes(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/relationships/r-1").mock(
            return_value=httpx.Response(200, json=_rel()),
        )
        delete = respx_mock.delete(f"{BASE}/api/relationships/r-1").mock(
            return_value=httpx.Response(204),
        )
        await pat_client.delete_relationship("r-1")
        assert delete.calls.last.request.headers["If-Match"] == "3"
