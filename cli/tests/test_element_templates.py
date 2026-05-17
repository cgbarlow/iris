"""CLI tests for element templates surface (ADR-191, v6.8.0).

Covers:
- ``iris create element-template`` body forwarding (set-scoped + global).
- ``iris update element-template`` partial-update body wiring.
- ``iris element-templates list / get / delete`` round-trips.
- ``iris create element --template-id`` extending the existing
  element-create command.
"""

from __future__ import annotations

import json

import httpx
import respx
from typer.testing import CliRunner

from iris_cli.main import app

runner = CliRunner()
BASE = "http://iris.test"


def _invoke(*args: str) -> tuple[int, str, str]:
    result = runner.invoke(app, list(args), catch_exceptions=False)
    return result.exit_code, result.stdout, result.stderr


def _template(**overrides) -> dict:
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
        "template_data": {"name": "El", "description": "d"},
        "created_by": "u",
        "created_by_username": "user",
        "created_at": "2026-05-17T00:00:00+00:00",
        "updated_at": "2026-05-17T00:00:00+00:00",
    }
    base.update(overrides)
    return base


class TestCreateTemplate:
    def test_create_set_scoped_template(
        self, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.post(f"{BASE}/api/element-templates").mock(
            return_value=httpx.Response(201, json=_template()),
        )
        code, out, _ = _invoke(
            "create", "element-template",
            "--source-element", "el-1",
            "--name", "Tpl",
            "--include", "name,description,data",
            "--set-id", "s-1",
        )
        assert code == 0, out
        body = json.loads(route.calls[0].request.content)
        assert body["source_element_id"] == "el-1"
        assert body["name"] == "Tpl"
        assert body["included_fields"] == ["name", "description", "data"]
        assert body["set_id"] == "s-1"
        assert body["is_global"] is False

    def test_create_global_template(
        self, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.post(f"{BASE}/api/element-templates").mock(
            return_value=httpx.Response(
                201, json=_template(set_id=None, set_name=None, is_global=True),
            ),
        )
        code, out, _ = _invoke(
            "create", "element-template",
            "--source-element", "el-1",
            "--name", "Tpl",
            "--include", "name",
            "--global",
        )
        assert code == 0, out
        body = json.loads(route.calls[0].request.content)
        assert body["is_global"] is True
        assert "set_id" not in body


class TestListGetDelete:
    def test_list_forwards_filters(
        self, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get(f"{BASE}/api/element-templates").mock(
            return_value=httpx.Response(
                200,
                json={
                    "items": [_template()], "total": 1,
                    "page": 1, "page_size": 50,
                },
            ),
        )
        code, _out, _ = _invoke(
            "--json", "element-templates", "list",
            "--set-id", "s-1", "--include-global",
        )
        assert code == 0
        url = str(route.calls[0].request.url)
        assert "set_id=s-1" in url
        assert "include_global=True" in url or "include_global=true" in url

    def test_get_returns_template(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/element-templates/t-1").mock(
            return_value=httpx.Response(200, json=_template()),
        )
        code, out, _ = _invoke("element-templates", "get", "t-1")
        assert code == 0
        assert "t-1" in out

    def test_delete_calls_delete_endpoint(
        self, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.delete(f"{BASE}/api/element-templates/t-1").mock(
            return_value=httpx.Response(204),
        )
        code, out, _ = _invoke("element-templates", "delete", "t-1")
        assert code == 0, out
        assert route.called


class TestUpdateTemplate:
    def test_update_forwards_only_supplied_fields(
        self, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.put(f"{BASE}/api/element-templates/t-1").mock(
            return_value=httpx.Response(
                200, json=_template(name="Renamed"),
            ),
        )
        code, _out, _ = _invoke(
            "update", "element-template", "t-1", "--name", "Renamed",
        )
        assert code == 0
        body = json.loads(route.calls[0].request.content)
        assert body == {"name": "Renamed"}

    def test_update_promote_to_global_with_null_set(
        self, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.put(f"{BASE}/api/element-templates/t-1").mock(
            return_value=httpx.Response(
                200, json=_template(set_id=None, is_global=True),
            ),
        )
        code, _out, _ = _invoke(
            "update", "element-template", "t-1",
            "--global", "--set-id", "null",
        )
        assert code == 0
        body = json.loads(route.calls[0].request.content)
        assert body["is_global"] is True
        assert body["set_id"] is None


class TestCreateElementWithTemplate:
    def test_template_id_forwards_to_create_element(
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
        code, out, _ = _invoke(
            "create", "element",
            "--set-id", "s-1",
            "--template-id", "t-1",
        )
        assert code == 0, out
        body = json.loads(route.calls[0].request.content)
        assert body["template_id"] == "t-1"
        assert body["set_id"] == "s-1"
        # name and element_type omitted — template provides them.
        assert "name" not in body
        assert "element_type" not in body
