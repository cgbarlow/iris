"""Integration tests for element → package optional membership (ADR-184).

Covers:

- ``elements.package_id`` column exists after migrations.
- ``ElementCreate``/``ElementUpdate`` accept ``package_id``.
- Cross-field invariant between ``element.set_id`` and the referenced
  package's ``set_id`` (HTTP 422 on mismatch).
- ``GET /api/elements?package_id=...`` three-valued filter.
- ``GET /api/packages/{id}/elements`` paginated listing.
- ``GET /api/diagrams/{id}/relationships`` augmented with
  ``element_package_memberships`` for elements drawn on the diagram.

All tests run against the real FastAPI app + a temp SQLite database
(no mocks — protocol 9).

TDD: written before the implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.main import create_app
from app.startup import initialize_databases

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        debug=True,
        cors_origins=["http://localhost:5173"],
        database=DatabaseConfig(data_dir=str(tmp_path / "data")),
        auth=AuthConfig(
            jwt_secret="test-secret-key-that-is-at-least-32-bytes-long-for-hs256",
            argon2_time_cost=1,
            argon2_memory_cost=8192,
            argon2_parallelism=1,
        ),
    )


@pytest.fixture
async def client(app_config: AppConfig) -> AsyncIterator[httpx.AsyncClient]:
    application = create_app(app_config)
    db_manager = DatabaseManager(app_config)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test",
    ) as c:
        yield c
    await db_manager.close()


async def _auth_headers(client: httpx.AsyncClient) -> dict[str, str]:
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    tokens = resp.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _create_set(
    client: httpx.AsyncClient, headers: dict, name: str = "S",
) -> str:
    resp = await client.post("/api/sets", json={"name": name}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _create_package(
    client: httpx.AsyncClient,
    headers: dict,
    *,
    name: str = "P",
    set_id: str | None = None,
) -> str:
    body: dict = {"name": name}
    if set_id is not None:
        body["set_id"] = set_id
    resp = await client.post("/api/packages", json=body, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _create_element(
    client: httpx.AsyncClient,
    headers: dict,
    *,
    name: str = "E",
    set_id: str | None = None,
    package_id: str | None = None,
    element_type: str = "component",
) -> dict[str, object]:
    body: dict[str, object] = {
        "element_type": element_type,
        "name": name,
        "data": {},
    }
    if set_id is not None:
        body["set_id"] = set_id
    if package_id is not None:
        body["package_id"] = package_id
    resp = await client.post("/api/elements", json=body, headers=headers)
    return {"status": resp.status_code, "body": resp.json()}


class TestSchema:
    """The migration adds the column + an index."""

    async def test_create_element_with_package_id_returns_201(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers)
        pkg = await _create_package(client, headers, set_id=set_id)

        result = await _create_element(
            client, headers, set_id=set_id, package_id=pkg,
        )
        assert result["status"] == 201
        body = result["body"]
        assert body["package_id"] == pkg

    async def test_element_response_includes_package_name_on_read(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers)
        pkg = await _create_package(client, headers, name="Cool Pkg", set_id=set_id)
        created = await _create_element(
            client, headers, set_id=set_id, package_id=pkg,
        )
        element_id = created["body"]["id"]

        resp = await client.get(f"/api/elements/{element_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["package_id"] == pkg
        assert body["package_name"] == "Cool Pkg"


class TestInvariant:
    """Cross-field invariant between element.set_id and package.set_id."""

    async def test_mismatched_sets_returns_422(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_a = await _create_set(client, headers, name="A")
        set_b = await _create_set(client, headers, name="B")
        pkg_in_a = await _create_package(client, headers, set_id=set_a)

        result = await _create_element(
            client, headers, set_id=set_b, package_id=pkg_in_a,
        )
        assert result["status"] == 422

    async def test_matching_sets_succeeds(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers)
        pkg = await _create_package(client, headers, set_id=set_id)

        result = await _create_element(
            client, headers, set_id=set_id, package_id=pkg,
        )
        assert result["status"] == 201

    # NOTE: the invariant's "package has set_id=NULL" branch is
    # defensively coded but unreachable through the public API today —
    # ``create_package`` defaults set_id to DEFAULT_SET_ID. That branch
    # is left in the service for direct DB writes / future tools.


class TestUpdate:
    """update_element treats package_id as a tri-state.

    The client distinguishes "do not touch", "explicitly clear", and
    "set to a value". The HTTP shape encodes "clear" with JSON null
    and "do not touch" by omitting the key entirely.
    """

    async def test_update_clears_package_id(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers)
        pkg = await _create_package(client, headers, set_id=set_id)
        created = await _create_element(
            client, headers, set_id=set_id, package_id=pkg,
        )
        element_id = created["body"]["id"]
        version = created["body"]["current_version"]

        resp = await client.put(
            f"/api/elements/{element_id}",
            json={
                "name": "E",
                "data": {},
                "package_id": None,
            },
            headers={**headers, "If-Match": str(version)},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["package_id"] is None

    async def test_update_sets_package_id(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers)
        pkg = await _create_package(client, headers, set_id=set_id)
        created = await _create_element(
            client, headers, set_id=set_id,
        )
        element_id = created["body"]["id"]
        version = created["body"]["current_version"]

        resp = await client.put(
            f"/api/elements/{element_id}",
            json={
                "name": "E",
                "data": {},
                "package_id": pkg,
            },
            headers={**headers, "If-Match": str(version)},
        )
        assert resp.status_code == 200
        assert resp.json()["package_id"] == pkg

    async def test_omitting_package_id_leaves_value_untouched(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers)
        pkg = await _create_package(client, headers, set_id=set_id)
        created = await _create_element(
            client, headers, set_id=set_id, package_id=pkg,
        )
        element_id = created["body"]["id"]
        version = created["body"]["current_version"]

        resp = await client.put(
            f"/api/elements/{element_id}",
            json={
                "name": "Renamed",
                "data": {},
                # package_id deliberately omitted
            },
            headers={**headers, "If-Match": str(version)},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Renamed"
        assert body["package_id"] == pkg


class TestListFilter:
    """list_elements?package_id=... three-valued semantics (ADR-185)."""

    async def test_filter_by_specific_package(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers)
        pkg = await _create_package(client, headers, set_id=set_id)

        in_pkg = await _create_element(
            client, headers, set_id=set_id, package_id=pkg, name="In",
        )
        out_pkg = await _create_element(
            client, headers, set_id=set_id, name="Out",
        )

        resp = await client.get(f"/api/elements?package_id={pkg}")
        assert resp.status_code == 200
        ids = {e["id"] for e in resp.json()["items"]}
        assert in_pkg["body"]["id"] in ids
        assert out_pkg["body"]["id"] not in ids

    async def test_filter_null_sentinel_returns_unmembered(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers)
        pkg = await _create_package(client, headers, set_id=set_id)

        in_pkg = await _create_element(
            client, headers, set_id=set_id, package_id=pkg, name="In",
        )
        out_pkg = await _create_element(
            client, headers, set_id=set_id, name="Out",
        )

        resp = await client.get("/api/elements?package_id=null")
        assert resp.status_code == 200
        ids = {e["id"] for e in resp.json()["items"]}
        assert in_pkg["body"]["id"] not in ids
        assert out_pkg["body"]["id"] in ids

    async def test_filter_omitted_returns_all(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers)
        pkg = await _create_package(client, headers, set_id=set_id)

        in_pkg = await _create_element(
            client, headers, set_id=set_id, package_id=pkg, name="In",
        )
        out_pkg = await _create_element(
            client, headers, set_id=set_id, name="Out",
        )

        resp = await client.get(f"/api/elements?set_id={set_id}")
        assert resp.status_code == 200
        ids = {e["id"] for e in resp.json()["items"]}
        assert in_pkg["body"]["id"] in ids
        assert out_pkg["body"]["id"] in ids


class TestPackageElementsEndpoint:
    """GET /api/packages/{id}/elements paginates."""

    async def test_returns_only_members(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers)
        pkg_a = await _create_package(client, headers, name="A", set_id=set_id)
        pkg_b = await _create_package(client, headers, name="B", set_id=set_id)

        in_a = await _create_element(
            client, headers, set_id=set_id, package_id=pkg_a, name="A1",
        )
        in_b = await _create_element(
            client, headers, set_id=set_id, package_id=pkg_b, name="B1",
        )

        resp = await client.get(f"/api/packages/{pkg_a}/elements")
        assert resp.status_code == 200
        body = resp.json()
        ids = {e["id"] for e in body["items"]}
        assert in_a["body"]["id"] in ids
        assert in_b["body"]["id"] not in ids
        assert body["total"] == 1

    async def test_empty_package_returns_empty_list(
        self, client: httpx.AsyncClient,
    ) -> None:
        """Issue #166: empty package returns 200 + [], not an error."""
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers)
        pkg = await _create_package(client, headers, set_id=set_id)

        resp = await client.get(f"/api/packages/{pkg}/elements")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    async def test_page_size_200_accepted(
        self, client: httpx.AsyncClient,
    ) -> None:
        """Issue #166 root cause: frontend asked page_size=200 and the
        router's ``le=100`` cap returned 422. The cap is now ``le=500``
        so the relationships tab loads.
        """
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers)
        pkg = await _create_package(client, headers, set_id=set_id)
        await _create_element(
            client, headers, set_id=set_id, package_id=pkg, name="Only",
        )

        resp = await client.get(
            f"/api/packages/{pkg}/elements?page_size=200",
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["page_size"] == 200
        assert body["total"] == 1
        assert len(body["items"]) == 1

    async def test_page_size_over_cap_returns_422(
        self, client: httpx.AsyncClient,
    ) -> None:
        """Cap is raised to 500 — anything beyond still 422."""
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers)
        pkg = await _create_package(client, headers, set_id=set_id)

        resp = await client.get(
            f"/api/packages/{pkg}/elements?page_size=501",
        )
        assert resp.status_code == 422


class TestDiagramRelationshipsAugmentation:
    """GET /api/diagrams/{id}/relationships gains element_package_memberships."""

    async def _create_diagram(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        *,
        set_id: str,
        elements_on_canvas: list[str],
    ) -> str:
        nodes = [
            {"id": f"n{i}", "data": {"entityId": eid}}
            for i, eid in enumerate(elements_on_canvas)
        ]
        resp = await client.post(
            "/api/diagrams",
            json={
                "diagram_type": "component",
                "name": "Test",
                "set_id": set_id,
                "data": {"nodes": nodes, "edges": []},
            },
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        return resp.json()["id"]

    async def test_response_contains_memberships_for_drawn_elements(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers)
        pkg = await _create_package(client, headers, name="Pkg", set_id=set_id)

        e_in = await _create_element(
            client, headers, set_id=set_id, package_id=pkg, name="E-in",
        )
        e_out = await _create_element(
            client, headers, set_id=set_id, name="E-out",
        )
        # Both elements are drawn on the diagram; only e_in has a package.
        diagram_id = await self._create_diagram(
            client, headers, set_id=set_id,
            elements_on_canvas=[e_in["body"]["id"], e_out["body"]["id"]],
        )

        resp = await client.get(f"/api/diagrams/{diagram_id}/relationships")
        assert resp.status_code == 200
        body = resp.json()
        assert "element_package_memberships" in body
        memberships = body["element_package_memberships"]
        assert len(memberships) == 1
        m = memberships[0]
        assert m["element_id"] == e_in["body"]["id"]
        assert m["element_name"] == "E-in"
        assert m["package_id"] == pkg
        assert m["package_name"] == "Pkg"

    async def test_response_omits_undrawn_elements(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers)
        pkg = await _create_package(client, headers, set_id=set_id)

        e_offcanvas = await _create_element(
            client, headers, set_id=set_id, package_id=pkg, name="Off",
        )
        diagram_id = await self._create_diagram(
            client, headers, set_id=set_id, elements_on_canvas=[],
        )

        resp = await client.get(f"/api/diagrams/{diagram_id}/relationships")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("element_package_memberships", []) == []
        _ = e_offcanvas  # silence unused
