"""Integration tests for batch element create + update (v6.10.0, ADR-200, #173 item 6).

New tools:

- POST /api/batch/elements/create — bulk create
- POST /api/batch/elements/update — bulk update with per-item optimistic concurrency

Per-item failure isolation: one bad item doesn't sink the whole batch.
The response includes a `BatchResultWithIds` envelope: succeeded count,
failed count, errors list, and the IDs of created/updated items.

Same fixture pattern as test_operations.py.
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
    assert r.status_code == 201
    return r.json()["id"]


class TestBatchCreateElements:
    async def test_create_three_elements_in_one_call(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_id = await _create_set(client, h)

        resp = await client.post(
            "/api/batch/elements/create",
            json={"elements": [
                {"element_type": "component", "name": "Apples", "data": {}, "set_id": set_id},
                {"element_type": "component", "name": "Bananas", "data": {}, "set_id": set_id},
                {"element_type": "component", "name": "Cherries", "data": {}, "set_id": set_id},
            ]},
            headers=h,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["succeeded"] == 3
        assert body["failed"] == 0
        assert body["errors"] == []
        assert len(body["ids"]) == 3

        list_resp = await client.get(f"/api/elements?set_id={set_id}", headers=h)
        names = [e["name"] for e in list_resp.json()["items"]]
        assert {"Apples", "Bananas", "Cherries"}.issubset(set(names))

    async def test_partial_failure_isolated_per_item(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_id = await _create_set(client, h)

        resp = await client.post(
            "/api/batch/elements/create",
            json={"elements": [
                {"element_type": "component", "name": "Valid1", "data": {}, "set_id": set_id},
                {"element_type": "",          "name": "InvalidType", "data": {}, "set_id": set_id},
                {"element_type": "component", "name": "Valid2", "data": {}, "set_id": set_id},
            ]},
            headers=h,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["succeeded"] == 2
        assert body["failed"] == 1
        assert len(body["errors"]) == 1
        assert "index 1" in body["errors"][0].lower() or "1" in body["errors"][0]
        assert len(body["ids"]) == 2

    async def test_empty_elements_returns_422(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        resp = await client.post(
            "/api/batch/elements/create",
            json={"elements": []},
            headers=h,
        )
        assert resp.status_code == 422

    async def test_requires_auth(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/api/batch/elements/create",
            json={"elements": [{"element_type": "component", "name": "X", "data": {}}]},
        )
        assert resp.status_code == 401


class TestBatchUpdateElements:
    async def test_update_two_elements_in_one_call(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_id = await _create_set(client, h)

        e1 = (await client.post(
            "/api/elements",
            json={"element_type": "component", "name": "Old1", "data": {}, "set_id": set_id},
            headers=h,
        )).json()
        e2 = (await client.post(
            "/api/elements",
            json={"element_type": "component", "name": "Old2", "data": {}, "set_id": set_id},
            headers=h,
        )).json()

        resp = await client.post(
            "/api/batch/elements/update",
            json={"updates": [
                {"element_id": e1["id"], "expected_version": e1["current_version"], "name": "New1", "data": {}},
                {"element_id": e2["id"], "expected_version": e2["current_version"], "name": "New2", "data": {}},
            ]},
            headers=h,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["succeeded"] == 2
        assert body["failed"] == 0
        assert sorted(body["ids"]) == sorted([e1["id"], e2["id"]])

        fresh1 = (await client.get(f"/api/elements/{e1['id']}", headers=h)).json()
        fresh2 = (await client.get(f"/api/elements/{e2['id']}", headers=h)).json()
        assert fresh1["name"] == "New1"
        assert fresh2["name"] == "New2"

    async def test_version_conflict_isolated_per_item(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_id = await _create_set(client, h)

        e1 = (await client.post(
            "/api/elements",
            json={"element_type": "component", "name": "E1", "data": {}, "set_id": set_id},
            headers=h,
        )).json()
        e2 = (await client.post(
            "/api/elements",
            json={"element_type": "component", "name": "E2", "data": {}, "set_id": set_id},
            headers=h,
        )).json()

        # Bump e1's version out from under the batch with a singular PUT.
        await client.put(
            f"/api/elements/{e1['id']}",
            json={"name": "E1-bumped", "data": {}},
            headers={**h, "If-Match": str(e1["current_version"])},
        )

        resp = await client.post(
            "/api/batch/elements/update",
            json={"updates": [
                # Stale expected_version on e1 — should fail.
                {"element_id": e1["id"], "expected_version": e1["current_version"], "name": "E1-batch", "data": {}},
                # Fresh expected_version on e2 — should succeed.
                {"element_id": e2["id"], "expected_version": e2["current_version"], "name": "E2-batch", "data": {}},
            ]},
            headers=h,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["succeeded"] == 1
        assert body["failed"] == 1
        assert e2["id"] in body["ids"]
        assert e1["id"] not in body["ids"]

    async def test_empty_updates_returns_422(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        resp = await client.post(
            "/api/batch/elements/update",
            json={"updates": []},
            headers=h,
        )
        assert resp.status_code == 422
