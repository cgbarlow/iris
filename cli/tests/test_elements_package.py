"""CLI tests for element ↔ package surface (ADR-184).

Covers:
- ``iris create element --package-id`` round-trip.
- ``iris elements list --package-id <uuid>`` and ``--package-id null``.
- ``iris update element --package-id <uuid>`` and ``--package-id null``.
- ``iris packages list-elements <pkg>`` paginated listing.
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


def _element_payload(**overrides: object) -> dict:
    return {
        "id": "el1",
        "element_type": "component",
        "current_version": 1,
        "name": "E",
        "description": None,
        "data": {},
        "created_at": "2026",
        "created_by": "u",
        "updated_at": "2026",
        "set_id": "s1",
        "package_id": None,
        "package_name": None,
        "notation": "simple",
        **overrides,
    }


class TestCreate:
    def test_create_element_with_package_id_forwards_field(
        self, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.post(f"{BASE}/api/elements").mock(
            return_value=httpx.Response(
                201, json=_element_payload(package_id="p1"),
            ),
        )
        code, out, _ = _invoke(
            "create", "element",
            "--name", "E", "--element-type", "component",
            "--set-id", "s1", "--package-id", "p1",
        )
        assert code == 0, out
        body = json.loads(route.calls[0].request.content)
        assert body["package_id"] == "p1"


class TestListFilter:
    def test_list_elements_filter_by_package(
        self, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get(f"{BASE}/api/elements").mock(
            return_value=httpx.Response(
                200, json={
                    "items": [_element_payload(id="e1", package_id="p1")],
                    "total": 1, "page": 1, "page_size": 50,
                },
            ),
        )
        code, _out, _ = _invoke(
            "elements", "list", "--package-id", "p1",
        )
        assert code == 0
        url = str(route.calls[0].request.url)
        assert "package_id=p1" in url

    def test_list_elements_filter_null_sentinel(
        self, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get(f"{BASE}/api/elements").mock(
            return_value=httpx.Response(
                200, json={"items": [], "total": 0, "page": 1, "page_size": 50},
            ),
        )
        code, _out, _ = _invoke(
            "elements", "list", "--package-id", "null",
        )
        assert code == 0
        url = str(route.calls[0].request.url)
        assert "package_id=null" in url


class TestUpdate:
    def test_update_element_set_package_id(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/elements/el1").mock(
            return_value=httpx.Response(
                200, json=_element_payload(id="el1", current_version=3),
            ),
        )
        put_route = respx_mock.put(f"{BASE}/api/elements/el1").mock(
            return_value=httpx.Response(
                200, json=_element_payload(id="el1", package_id="p1"),
            ),
        )
        code, _out, _ = _invoke(
            "update", "element", "el1", "--package-id", "p1",
        )
        assert code == 0
        body = json.loads(put_route.calls[0].request.content)
        assert body["package_id"] == "p1"

    def test_update_element_clear_package_id_with_null(
        self, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/elements/el1").mock(
            return_value=httpx.Response(
                200,
                json=_element_payload(id="el1", package_id="p1", current_version=4),
            ),
        )
        put_route = respx_mock.put(f"{BASE}/api/elements/el1").mock(
            return_value=httpx.Response(
                200, json=_element_payload(id="el1", package_id=None),
            ),
        )
        code, _out, _ = _invoke(
            "update", "element", "el1", "--package-id", "null",
        )
        assert code == 0
        body = json.loads(put_route.calls[0].request.content)
        assert body["package_id"] is None

    def test_omitting_package_id_keeps_value(
        self, respx_mock: respx.Router,
    ) -> None:
        """No --package-id flag → the JSON body must not include the
        key at all (so the backend's tri-state sentinel leaves the
        column untouched)."""
        respx_mock.get(f"{BASE}/api/elements/el1").mock(
            return_value=httpx.Response(
                200,
                json=_element_payload(id="el1", package_id="p1", current_version=5),
            ),
        )
        put_route = respx_mock.put(f"{BASE}/api/elements/el1").mock(
            return_value=httpx.Response(
                200, json=_element_payload(id="el1", package_id="p1"),
            ),
        )
        code, _out, _ = _invoke(
            "update", "element", "el1", "--name", "Renamed",
        )
        assert code == 0
        body = json.loads(put_route.calls[0].request.content)
        assert "package_id" not in body


class TestPackagesListElements:
    def test_lists_via_package_elements_endpoint(
        self, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get(f"{BASE}/api/packages/p1/elements").mock(
            return_value=httpx.Response(
                200, json={
                    "items": [
                        _element_payload(id="e1", package_id="p1"),
                        _element_payload(id="e2", name="E2", package_id="p1"),
                    ],
                    "total": 2, "page": 1, "page_size": 50,
                },
            ),
        )
        code, out, _ = _invoke("packages", "list-elements", "p1")
        assert code == 0, out
        assert route.called
