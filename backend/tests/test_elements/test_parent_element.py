"""Integration tests for element → element containment (ADR-231).

Covers:
- creating/updating an element with ``parent_element_id`` (tri-state);
- validation: parent exists (422), same-set only (422), no cycles (422),
  no self-parent (422);
- ``get``/``list`` expose ``parent_element_id`` + ``parent_element_name``;
- ``GET /api/elements/{id}/children`` and ``/ancestors``.

Real FastAPI app + temp SQLite database (no mocks — protocol 9). TDD.
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
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await db_manager.close()


async def _auth(client: httpx.AsyncClient) -> dict[str, str]:
    await client.post("/api/auth/setup", json={"username": "admin", "password": "AdminPass123!"})
    resp = await client.post("/api/auth/login", json={"username": "admin", "password": "AdminPass123!"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _set(client: httpx.AsyncClient, headers: dict, name: str = "S") -> str:
    resp = await client.post("/api/sets", json={"name": name}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _elem(
    client: httpx.AsyncClient,
    headers: dict,
    *,
    name: str = "E",
    set_id: str | None = None,
    parent_element_id: str | None = None,
) -> dict:
    body: dict[str, object] = {"element_type": "capability", "name": name, "data": {}}
    if set_id is not None:
        body["set_id"] = set_id
    if parent_element_id is not None:
        body["parent_element_id"] = parent_element_id
    resp = await client.post("/api/elements", json=body, headers=headers)
    return {"status": resp.status_code, "body": resp.json()}


async def _update_parent(client, headers, eid, ver, parent):  # noqa: ANN001
    return await client.put(
        f"/api/elements/{eid}",
        json={"name": "E", "data": {}, "parent_element_id": parent},
        headers={**headers, "If-Match": str(ver)},
    )


class TestCreateAndRead:
    async def test_create_with_parent_persists_and_round_trips(self, client):
        h = await _auth(client)
        s = await _set(client, h)
        zone = await _elem(client, h, name="Zone", set_id=s)
        child = await _elem(client, h, name="Cap", set_id=s, parent_element_id=zone["body"]["id"])
        assert child["status"] == 201, child
        assert child["body"]["parent_element_id"] == zone["body"]["id"]

        resp = await client.get(f"/api/elements/{child['body']['id']}")
        assert resp.status_code == 200
        assert resp.json()["parent_element_id"] == zone["body"]["id"]
        assert resp.json()["parent_element_name"] == "Zone"

    async def test_create_with_missing_parent_returns_422(self, client):
        h = await _auth(client)
        s = await _set(client, h)
        child = await _elem(
            client, h, set_id=s,
            parent_element_id="00000000-0000-0000-0000-000000000000",
        )
        assert child["status"] == 422, child

    async def test_cross_set_parent_rejected(self, client):
        h = await _auth(client)
        a = await _set(client, h, name="A")
        b = await _set(client, h, name="B")
        zone_b = await _elem(client, h, name="ZB", set_id=b)
        child = await _elem(client, h, set_id=a, parent_element_id=zone_b["body"]["id"])
        assert child["status"] == 422, child


class TestUpdate:
    async def test_update_sets_and_clears_parent(self, client):
        h = await _auth(client)
        s = await _set(client, h)
        zone = await _elem(client, h, name="Zone", set_id=s)
        child = await _elem(client, h, name="Cap", set_id=s)
        eid, ver = child["body"]["id"], child["body"]["current_version"]

        r = await _update_parent(client, h, eid, ver, zone["body"]["id"])
        assert r.status_code == 200, r.text
        assert r.json()["parent_element_id"] == zone["body"]["id"]

        r2 = await _update_parent(client, h, eid, r.json()["current_version"], None)
        assert r2.status_code == 200, r2.text
        assert r2.json()["parent_element_id"] is None

    async def test_update_omitting_leaves_untouched(self, client):
        h = await _auth(client)
        s = await _set(client, h)
        zone = await _elem(client, h, name="Zone", set_id=s)
        child = await _elem(client, h, name="Cap", set_id=s, parent_element_id=zone["body"]["id"])
        eid, ver = child["body"]["id"], child["body"]["current_version"]
        r = await client.put(
            f"/api/elements/{eid}",
            json={"name": "Renamed", "data": {}},  # parent omitted
            headers={**h, "If-Match": str(ver)},
        )
        assert r.status_code == 200, r.text
        assert r.json()["parent_element_id"] == zone["body"]["id"]

    async def test_self_parent_rejected(self, client):
        h = await _auth(client)
        s = await _set(client, h)
        e = await _elem(client, h, name="E", set_id=s)
        eid, ver = e["body"]["id"], e["body"]["current_version"]
        r = await _update_parent(client, h, eid, ver, eid)
        assert r.status_code == 422, r.text

    async def test_cycle_rejected(self, client):
        h = await _auth(client)
        s = await _set(client, h)
        a = await _elem(client, h, name="A", set_id=s)
        b = await _elem(client, h, name="B", set_id=s, parent_element_id=a["body"]["id"])
        # Now make A a child of B → cycle A→B→A.
        r = await _update_parent(client, h, a["body"]["id"], a["body"]["current_version"], b["body"]["id"])
        assert r.status_code == 422, r.text


class TestChildrenAndAncestors:
    async def test_children_and_ancestors(self, client):
        h = await _auth(client)
        s = await _set(client, h)
        zone = await _elem(client, h, name="Zone", set_id=s)
        cap = await _elem(client, h, name="Cap", set_id=s, parent_element_id=zone["body"]["id"])
        sub = await _elem(client, h, name="Sub", set_id=s, parent_element_id=cap["body"]["id"])

        kids = await client.get(f"/api/elements/{zone['body']['id']}/children")
        assert kids.status_code == 200, kids.text
        assert [k["name"] for k in kids.json()] == ["Cap"]

        anc = await client.get(f"/api/elements/{sub['body']['id']}/ancestors")
        assert anc.status_code == 200, anc.text
        # root-first breadcrumb: Zone, Cap.
        assert [a["name"] for a in anc.json()] == ["Zone", "Cap"]
