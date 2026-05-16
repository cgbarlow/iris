"""MCP tests for the v6.7.4 ``create_element`` package_id parameter
(ADR-188, issue #154).

Closes the surface-parity gap left after v6.7.0 (ADR-184): backend +
CLI already accept package_id on create; only the MCP tool had to be
extended to forward it. These tests assert that:

- ``create_element`` tool schema advertises ``package_id``.
- The MCP handler forwards a non-null ``package_id`` to the REST POST
  body.
- Omitting ``package_id`` from the args leaves it out of the body
  (the backend defaults it to ``None``).
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
        "id": "el-new",
        "element_type": "component",
        "current_version": 1,
        "name": "New Element",
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


class TestSchema:
    def test_create_element_schema_includes_package_id(self) -> None:
        defs = {t.name: t for t in tools.tool_definitions()}
        props = defs["create_element"].inputSchema["properties"]
        assert "package_id" in props
        # package_id must NOT be required — it's an optional convenience.
        assert "package_id" not in defs["create_element"].inputSchema.get(
            "required", [],
        )


class TestCreateElementWithPackage:
    @pytest.mark.anyio
    async def test_forwards_package_id_to_body(
        self, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.post(f"{BASE}/api/elements").mock(
            return_value=httpx.Response(
                201, json=_element_response(package_id="p1", package_name="Pkg"),
            ),
        )
        async with IrisClient(BASE) as c:
            await tools._create_element(
                c,
                {
                    "element_type": "component",
                    "name": "New Element",
                    "set_id": "s1",
                    "package_id": "p1",
                },
            )
        body = json.loads(route.calls[0].request.content)
        assert body["package_id"] == "p1"
        assert body["set_id"] == "s1"
        assert body["element_type"] == "component"
        assert body["name"] == "New Element"

    @pytest.mark.anyio
    async def test_omitting_package_id_keeps_it_out_of_body(
        self, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.post(f"{BASE}/api/elements").mock(
            return_value=httpx.Response(
                201, json=_element_response(),
            ),
        )
        async with IrisClient(BASE) as c:
            await tools._create_element(
                c,
                {
                    "element_type": "component",
                    "name": "New Element",
                    "set_id": "s1",
                },
            )
        body = json.loads(route.calls[0].request.content)
        assert "package_id" not in body

    @pytest.mark.anyio
    async def test_explicit_null_package_id_is_dropped(
        self, respx_mock: respx.Router,
    ) -> None:
        """Passing package_id=None should behave the same as omitting it
        (the create surface has no tri-state semantics; only update does)."""
        route = respx_mock.post(f"{BASE}/api/elements").mock(
            return_value=httpx.Response(
                201, json=_element_response(),
            ),
        )
        async with IrisClient(BASE) as c:
            await tools._create_element(
                c,
                {
                    "element_type": "component",
                    "name": "New Element",
                    "set_id": "s1",
                    "package_id": None,
                },
            )
        body = json.loads(route.calls[0].request.content)
        assert "package_id" not in body
