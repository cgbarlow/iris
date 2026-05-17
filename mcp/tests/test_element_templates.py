"""MCP tests for element templates surface (ADR-191, v6.8.0,
issue #153).

Covers:

- Five new tools registered: create/list/get/update/delete
  element_template.
- create_element gains optional ``template_id`` parameter and forwards
  it to the REST POST body.
- Body forwarding for create/update template (included_fields,
  is_global, set_id semantics).
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from iris_client import IrisClient

from iris_mcp import tools

BASE = "http://iris.test"


def _template_response(**overrides):
    base = {
        "id": "t-1",
        "name": "Tpl",
        "description": None,
        "set_id": "s-1",
        "set_name": "S",
        "is_global": False,
        "source_element_id": "el-1",
        "source_element_name": "El",
        "included_fields": ["name", "description"],
        "template_data": {"name": "El", "description": "from-source"},
        "created_by": "u",
        "created_by_username": "user",
        "created_at": "2026-05-17T00:00:00+00:00",
        "updated_at": "2026-05-17T00:00:00+00:00",
    }
    base.update(overrides)
    return base


class TestInventory:
    def test_five_new_tools_registered(self) -> None:
        names = {t.name for t in tools.tool_definitions()}
        expected = {
            "create_element_template",
            "list_element_templates",
            "get_element_template",
            "update_element_template",
            "delete_element_template",
        }
        assert expected <= names

    def test_create_element_schema_includes_template_id(self) -> None:
        defs = {t.name: t for t in tools.tool_definitions()}
        props = defs["create_element"].inputSchema["properties"]
        assert "template_id" in props

    def test_create_element_required_relaxed(self) -> None:
        """When template_id is supplied, element_type and name may
        come from the template — they must not be required at the
        MCP schema level."""
        defs = {t.name: t for t in tools.tool_definitions()}
        required = defs["create_element"].inputSchema.get("required", [])
        assert "element_type" not in required
        assert "name" not in required

    def test_create_element_template_required_fields(self) -> None:
        defs = {t.name: t for t in tools.tool_definitions()}
        required = defs["create_element_template"].inputSchema["required"]
        assert "source_element_id" in required
        assert "name" in required
        assert "included_fields" in required


class TestCreateElementTemplateForward:
    @pytest.mark.anyio
    async def test_forwards_full_body(
        self, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.post(f"{BASE}/api/element-templates").mock(
            return_value=httpx.Response(201, json=_template_response()),
        )
        async with IrisClient(BASE) as c:
            await tools._create_element_template(c, {
                "source_element_id": "el-1",
                "name": "Tpl",
                "description": "d",
                "included_fields": ["name", "description"],
                "set_id": "s-1",
                "is_global": False,
            })
        body = json.loads(route.calls[0].request.content)
        assert body == {
            "source_element_id": "el-1",
            "name": "Tpl",
            "description": "d",
            "included_fields": ["name", "description"],
            "set_id": "s-1",
            "is_global": False,
        }

    @pytest.mark.anyio
    async def test_global_omits_set_id(
        self, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.post(f"{BASE}/api/element-templates").mock(
            return_value=httpx.Response(
                201, json=_template_response(set_id=None, is_global=True),
            ),
        )
        async with IrisClient(BASE) as c:
            await tools._create_element_template(c, {
                "source_element_id": "el-1",
                "name": "Tpl",
                "included_fields": ["name"],
                "is_global": True,
            })
        body = json.loads(route.calls[0].request.content)
        assert body["is_global"] is True
        assert "set_id" not in body


class TestListGetUpdateDelete:
    @pytest.mark.anyio
    async def test_list_forwards_filters(
        self, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get(f"{BASE}/api/element-templates").mock(
            return_value=httpx.Response(
                200, json={
                    "items": [_template_response()],
                    "total": 1, "page": 1, "page_size": 50,
                },
            ),
        )
        async with IrisClient(BASE) as c:
            await tools._list_element_templates(c, {
                "set_id": "s-1", "include_global": False,
                "page": 2, "limit": 10,
            })
        url = str(route.calls[0].request.url)
        assert "set_id=s-1" in url
        assert "include_global=False" in url or "include_global=false" in url
        assert "page=2" in url
        assert "page_size=10" in url

    @pytest.mark.anyio
    async def test_get_returns_template(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/element-templates/t-1").mock(
            return_value=httpx.Response(200, json=_template_response()),
        )
        async with IrisClient(BASE) as c:
            result = await tools._get_element_template(c, {"template_id": "t-1"})
        assert "t-1" in result

    @pytest.mark.anyio
    async def test_update_forwards_only_supplied_fields(
        self, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.put(f"{BASE}/api/element-templates/t-1").mock(
            return_value=httpx.Response(
                200, json=_template_response(name="Renamed"),
            ),
        )
        async with IrisClient(BASE) as c:
            await tools._update_element_template(c, {
                "template_id": "t-1", "name": "Renamed",
            })
        body = json.loads(route.calls[0].request.content)
        assert body == {"name": "Renamed"}

    @pytest.mark.anyio
    async def test_update_promote_to_global_forwards_null_set_id(
        self, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.put(f"{BASE}/api/element-templates/t-1").mock(
            return_value=httpx.Response(
                200, json=_template_response(set_id=None, is_global=True),
            ),
        )
        async with IrisClient(BASE) as c:
            await tools._update_element_template(c, {
                "template_id": "t-1",
                "is_global": True,
                "set_id": None,
            })
        body = json.loads(route.calls[0].request.content)
        assert body["is_global"] is True
        assert body["set_id"] is None

    @pytest.mark.anyio
    async def test_delete_returns_success_payload(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.delete(f"{BASE}/api/element-templates/t-1").mock(
            return_value=httpx.Response(204),
        )
        async with IrisClient(BASE) as c:
            result = await tools._delete_element_template(
                c, {"template_id": "t-1"},
            )
        body = json.loads(result)
        assert body["success"] is True
        assert body["template_id"] == "t-1"
        assert body["deleted"] is True


class TestCreateElementWithTemplate:
    @pytest.mark.anyio
    async def test_forwards_template_id_to_body(
        self, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.post(f"{BASE}/api/elements").mock(
            return_value=httpx.Response(201, json={
                "id": "el-new", "element_type": "component",
                "current_version": 1, "name": "Templated",
                "description": None, "data": {}, "set_id": "s-1",
                "package_id": None, "package_name": None,
                "notation": "simple",
                "created_at": "2026-05-17T00:00:00+00:00",
                "created_by": "u",
                "updated_at": "2026-05-17T00:00:00+00:00",
            }),
        )
        async with IrisClient(BASE) as c:
            await tools._create_element(c, {
                "set_id": "s-1",
                "template_id": "t-1",
            })
        body = json.loads(route.calls[0].request.content)
        assert body["template_id"] == "t-1"
        assert body["set_id"] == "s-1"
        # element_type / name are absent (template fills them).
        assert "element_type" not in body
        assert "name" not in body
