"""Integration tests for element templates (ADR-191, issue #153).

Covers:

- CRUD on /api/element-templates (create/get/list/update/delete).
- Scoping: set-scoped, global, and the CHECK constraint that ties
  is_global to set_id.
- Field whitelisting: non-whitelisted fields are dropped from
  included_fields silently.
- Re-projection on update when included_fields changes.
- ``POST /api/elements?template_id=…`` pre-fill with explicit request
  fields winning.
- Tags are written through to element_tags when included.

All tests use the real FastAPI app + a temp SQLite database
(no mocks — Protocol §9). TDD: written before / alongside the
implementation.
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


async def _auth(client: httpx.AsyncClient) -> dict[str, str]:
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _create_set(c: httpx.AsyncClient, h: dict, name: str = "S") -> str:
    r = await c.post("/api/sets", json={"name": name}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _create_element(
    c: httpx.AsyncClient, h: dict, *, set_id: str, **extra,
) -> dict:
    body = {
        "element_type": "component",
        "name": "Source Element",
        "description": "from-element description",
        "data": {"k": "v"},
        "metadata": {"author": "me"},
        "notation": "simple",
        "set_id": set_id,
        **extra,
    }
    r = await c.post("/api/elements", json=body, headers=h)
    assert r.status_code == 201, r.text
    # Add a tag so we can test the tags path.
    el_id = r.json()["id"]
    await c.post(
        f"/api/elements/{el_id}/tags",
        json={"tag": "alpha"}, headers=h,
    )
    return r.json()


class TestCreate:
    async def test_create_template_from_element_set_scoped(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_id = await _create_set(client, h)
        el = await _create_element(client, h, set_id=set_id)
        r = await client.post(
            "/api/element-templates",
            json={
                "source_element_id": el["id"],
                "name": "Tpl A",
                "description": "first template",
                "included_fields": ["name", "description", "data", "tags"],
                "set_id": set_id,
                "is_global": False,
            },
            headers=h,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["name"] == "Tpl A"
        assert body["is_global"] is False
        assert body["set_id"] == set_id
        assert set(body["included_fields"]) == {
            "name", "description", "data", "tags",
        }
        assert body["template_data"]["name"] == "Source Element"
        assert body["template_data"]["tags"] == ["alpha"]
        assert body["source_element_id"] == el["id"]

    async def test_create_global_template(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_id = await _create_set(client, h)
        el = await _create_element(client, h, set_id=set_id)
        r = await client.post(
            "/api/element-templates",
            json={
                "source_element_id": el["id"],
                "name": "Global Tpl",
                "included_fields": ["name", "element_type"],
                "set_id": None,
                "is_global": True,
            },
            headers=h,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["is_global"] is True
        assert body["set_id"] is None

    async def test_create_rejects_global_with_set_id(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_id = await _create_set(client, h)
        el = await _create_element(client, h, set_id=set_id)
        r = await client.post(
            "/api/element-templates",
            json={
                "source_element_id": el["id"],
                "name": "Bad Tpl",
                "included_fields": ["name"],
                "set_id": set_id,
                "is_global": True,
            },
            headers=h,
        )
        assert r.status_code == 422

    async def test_create_rejects_non_global_without_set_id(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_id = await _create_set(client, h)
        el = await _create_element(client, h, set_id=set_id)
        r = await client.post(
            "/api/element-templates",
            json={
                "source_element_id": el["id"],
                "name": "Bad Tpl",
                "included_fields": ["name"],
                "set_id": None,
                "is_global": False,
            },
            headers=h,
        )
        assert r.status_code == 422

    async def test_create_drops_non_whitelisted_fields_silently(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_id = await _create_set(client, h)
        el = await _create_element(client, h, set_id=set_id)
        r = await client.post(
            "/api/element-templates",
            json={
                "source_element_id": el["id"],
                "name": "Tpl Filtered",
                "included_fields": ["name", "id", "current_version", "evil"],
                "set_id": set_id,
                "is_global": False,
            },
            headers=h,
        )
        assert r.status_code == 201, r.text
        assert r.json()["included_fields"] == ["name"]

    async def test_create_rejects_unknown_source_element(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_id = await _create_set(client, h)
        r = await client.post(
            "/api/element-templates",
            json={
                "source_element_id": "does-not-exist",
                "name": "Tpl",
                "included_fields": ["name"],
                "set_id": set_id,
                "is_global": False,
            },
            headers=h,
        )
        assert r.status_code == 404


class TestListAndGet:
    async def test_list_set_scoped_plus_globals(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_a = await _create_set(client, h, name="A")
        set_b = await _create_set(client, h, name="B")
        el_a = await _create_element(client, h, set_id=set_a)
        el_b = await _create_element(client, h, set_id=set_b)
        # Two templates in A, one in B, one global.
        for n in ("A1", "A2"):
            r = await client.post(
                "/api/element-templates",
                json={
                    "source_element_id": el_a["id"], "name": n,
                    "included_fields": ["name"], "set_id": set_a,
                    "is_global": False,
                },
                headers=h,
            )
            assert r.status_code == 201
        r = await client.post(
            "/api/element-templates",
            json={
                "source_element_id": el_b["id"], "name": "B1",
                "included_fields": ["name"], "set_id": set_b,
                "is_global": False,
            },
            headers=h,
        )
        assert r.status_code == 201
        r = await client.post(
            "/api/element-templates",
            json={
                "source_element_id": el_a["id"], "name": "G1",
                "included_fields": ["name"], "set_id": None,
                "is_global": True,
            },
            headers=h,
        )
        assert r.status_code == 201

        # set_id=A + include_global → A's 2 + 1 global = 3
        r = await client.get(
            f"/api/element-templates?set_id={set_a}&include_global=true",
            headers=h,
        )
        assert r.status_code == 200
        names = sorted(t["name"] for t in r.json()["items"])
        assert names == ["A1", "A2", "G1"]

        # set_id=A + include_global=false → A's 2 only
        r = await client.get(
            f"/api/element-templates?set_id={set_a}&include_global=false",
            headers=h,
        )
        names = sorted(t["name"] for t in r.json()["items"])
        assert names == ["A1", "A2"]

        # set_id absent + include_global → globals only
        r = await client.get(
            "/api/element-templates?include_global=true", headers=h,
        )
        names = sorted(t["name"] for t in r.json()["items"])
        assert names == ["G1"]

    async def test_get_one_returns_full_template(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_id = await _create_set(client, h)
        el = await _create_element(client, h, set_id=set_id)
        r = await client.post(
            "/api/element-templates",
            json={
                "source_element_id": el["id"], "name": "T",
                "included_fields": ["name", "data"], "set_id": set_id,
                "is_global": False,
            },
            headers=h,
        )
        tid = r.json()["id"]
        r = await client.get(
            f"/api/element-templates/{tid}", headers=h,
        )
        assert r.status_code == 200
        assert r.json()["template_data"]["data"] == {"k": "v"}

    async def test_get_missing_template_returns_404(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        r = await client.get(
            "/api/element-templates/no-such-id", headers=h,
        )
        assert r.status_code == 404


class TestUpdate:
    async def test_update_reprojects_template_data(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_id = await _create_set(client, h)
        el = await _create_element(client, h, set_id=set_id)
        r = await client.post(
            "/api/element-templates",
            json={
                "source_element_id": el["id"], "name": "T",
                "included_fields": ["name"], "set_id": set_id,
                "is_global": False,
            },
            headers=h,
        )
        tid = r.json()["id"]
        # Expand included_fields to include description; expect a
        # fresh snapshot from the source element.
        r = await client.put(
            f"/api/element-templates/{tid}",
            json={"included_fields": ["name", "description"]},
            headers=h,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["included_fields"] == ["name", "description"]
        assert body["template_data"]["description"] == "from-element description"

    async def test_promote_to_global(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_id = await _create_set(client, h)
        el = await _create_element(client, h, set_id=set_id)
        r = await client.post(
            "/api/element-templates",
            json={
                "source_element_id": el["id"], "name": "T",
                "included_fields": ["name"], "set_id": set_id,
                "is_global": False,
            },
            headers=h,
        )
        tid = r.json()["id"]
        r = await client.put(
            f"/api/element-templates/{tid}",
            json={"is_global": True, "set_id": None},
            headers=h,
        )
        assert r.status_code == 200, r.text
        assert r.json()["is_global"] is True
        assert r.json()["set_id"] is None


class TestDelete:
    async def test_delete_soft_deletes(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_id = await _create_set(client, h)
        el = await _create_element(client, h, set_id=set_id)
        r = await client.post(
            "/api/element-templates",
            json={
                "source_element_id": el["id"], "name": "T",
                "included_fields": ["name"], "set_id": set_id,
                "is_global": False,
            },
            headers=h,
        )
        tid = r.json()["id"]
        r = await client.delete(
            f"/api/element-templates/{tid}", headers=h,
        )
        assert r.status_code == 204
        # Subsequent get → 404
        r = await client.get(f"/api/element-templates/{tid}", headers=h)
        assert r.status_code == 404


class TestApplyTemplate:
    async def test_create_element_with_template_pre_fills_fields(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_id = await _create_set(client, h)
        el = await _create_element(client, h, set_id=set_id)
        r = await client.post(
            "/api/element-templates",
            json={
                "source_element_id": el["id"], "name": "T",
                "included_fields": [
                    "name", "description", "element_type", "data", "tags",
                ],
                "set_id": set_id,
                "is_global": False,
            },
            headers=h,
        )
        tid = r.json()["id"]

        # Create a new element supplying only set_id + template_id;
        # template fills name, description, element_type, data, tags.
        r = await client.post(
            "/api/elements",
            json={"set_id": set_id, "template_id": tid},
            headers=h,
        )
        assert r.status_code == 201, r.text
        new_el = r.json()
        assert new_el["name"] == "Source Element"
        assert new_el["description"] == "from-element description"
        assert new_el["element_type"] == "component"
        assert new_el["data"] == {"k": "v"}
        assert new_el["tags"] == ["alpha"]

    async def test_explicit_fields_win_over_template(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_id = await _create_set(client, h)
        el = await _create_element(client, h, set_id=set_id)
        r = await client.post(
            "/api/element-templates",
            json={
                "source_element_id": el["id"], "name": "T",
                "included_fields": ["name", "description"],
                "set_id": set_id, "is_global": False,
            },
            headers=h,
        )
        tid = r.json()["id"]
        r = await client.post(
            "/api/elements",
            json={
                "set_id": set_id,
                "template_id": tid,
                "element_type": "component",
                "name": "Override Name",
            },
            headers=h,
        )
        assert r.status_code == 201, r.text
        new_el = r.json()
        assert new_el["name"] == "Override Name"
        # Description was not overridden → comes from template.
        assert new_el["description"] == "from-element description"

    async def test_missing_template_returns_404(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_id = await _create_set(client, h)
        r = await client.post(
            "/api/elements",
            json={
                "set_id": set_id,
                "template_id": "no-such-template",
                "element_type": "component",
                "name": "X",
            },
            headers=h,
        )
        assert r.status_code == 404

    async def test_template_captures_class_attributes(
        self, client: httpx.AsyncClient,
    ) -> None:
        """Issue #165: class element ``attributes`` are part of
        ``element_versions.data`` JSON, so checking the 'data' field
        in the dialog must round-trip them through the template into
        a new element.
        """
        h = await _auth(client)
        set_id = await _create_set(client, h)
        attrs = [
            {"name": "price", "type": "string", "scope": "Private"},
            {"name": "qty", "type": "int"},
        ]
        # Source element: a UML class with structured attributes.
        src = await client.post(
            "/api/elements",
            json={
                "set_id": set_id,
                "element_type": "class",
                "notation": "uml",
                "name": "Order",
                "data": {"attributes": attrs, "operations": ["ship()"]},
            },
            headers=h,
        )
        assert src.status_code == 201, src.text
        src_id = src.json()["id"]

        # Build a template that captures the data field only.
        tpl = await client.post(
            "/api/element-templates",
            json={
                "source_element_id": src_id,
                "name": "Class with attrs",
                "included_fields": ["element_type", "notation", "data"],
                "set_id": set_id,
                "is_global": False,
            },
            headers=h,
        )
        assert tpl.status_code == 201, tpl.text
        tpl_data = tpl.json()["template_data"]
        assert tpl_data["data"]["attributes"] == attrs
        assert tpl_data["data"]["operations"] == ["ship()"]

        # Create a new element from the template — attributes carry through.
        new_el = await client.post(
            "/api/elements",
            json={
                "set_id": set_id,
                "template_id": tpl.json()["id"],
                "name": "Order Copy",
            },
            headers=h,
        )
        assert new_el.status_code == 201, new_el.text
        body = new_el.json()
        assert body["element_type"] == "class"
        assert body["notation"] == "uml"
        assert body["data"]["attributes"] == attrs
        assert body["data"]["operations"] == ["ship()"]
