"""Tests for per-set hierarchy sort preference (v6.11.0, ADR-202).

Verifies that ``GET /api/diagrams/hierarchy?set_id=X`` honours the
set's ``hierarchy_sort`` column for ordering returned siblings.

Sort options:
- ``manual``  — current behaviour: node_type, sequence_order, name.
                Diagrams sort above packages within the same parent.
- ``alpha``   — alphabetical by name, no node_type tie-break.
- ``newest``  — created_at DESC.
- ``oldest``  — created_at ASC.

Default for new sets is ``manual``.
"""

from __future__ import annotations

import asyncio
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


async def _setup_mixed_set(c: httpx.AsyncClient, h: dict) -> str:
    """Create a set with two packages and two diagrams at root level,
    spread out in creation time so order-by-date is meaningful."""
    set_resp = await c.post("/api/sets", json={"name": "SortSet"}, headers=h)
    assert set_resp.status_code == 201
    set_id = set_resp.json()["id"]

    # Create in this order, with sleeps so created_at differs:
    #   1. Pkg "Zulu"
    #   2. Diag "Alpha"
    #   3. Pkg "Mike"
    #   4. Diag "Tango"
    await c.post(
        "/api/packages",
        json={"name": "Zulu", "set_id": set_id},
        headers=h,
    )
    await asyncio.sleep(0.01)
    await c.post(
        "/api/diagrams",
        json={"diagram_type": "simple-view", "name": "Alpha", "data": {}, "set_id": set_id},
        headers=h,
    )
    await asyncio.sleep(0.01)
    await c.post(
        "/api/packages",
        json={"name": "Mike", "set_id": set_id},
        headers=h,
    )
    await asyncio.sleep(0.01)
    await c.post(
        "/api/diagrams",
        json={"diagram_type": "simple-view", "name": "Tango", "data": {}, "set_id": set_id},
        headers=h,
    )

    return set_id


async def _names(c: httpx.AsyncClient, h: dict, set_id: str) -> list[str]:
    resp = await c.get(f"/api/diagrams/hierarchy?set_id={set_id}", headers=h)
    assert resp.status_code == 200, resp.text
    return [n["name"] for n in resp.json()]


class TestDefaultSort:
    async def test_new_set_defaults_to_manual(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_resp = await client.post(
            "/api/sets", json={"name": "DefaultSortTest"}, headers=h,
        )
        assert set_resp.status_code == 201
        body = set_resp.json()
        assert body["hierarchy_sort"] == "manual", (
            "default hierarchy_sort on new sets must be 'manual' so existing "
            "behaviour is preserved (ADR-202)"
        )

    async def test_existing_sets_keep_manual_order(
        self, client: httpx.AsyncClient,
    ) -> None:
        """Without explicitly setting hierarchy_sort, the order is unchanged
        from the historical default: diagrams above packages within the
        same parent, then sequence_order (auto-assigned in creation order
        per parent), then name as a final tiebreak."""
        h = await _auth(client)
        set_id = await _setup_mixed_set(client, h)
        names = await _names(client, h, set_id)
        # Manual sort: node_type ('diagram' < 'package' alphabetically).
        # Diagrams in creation order: Alpha (created at t1), Tango (at t3).
        # Packages in creation order: Zulu (at t0), Mike (at t2).
        # sequence_order is auto-incremented per parent group on creation
        # (packages/service.py:38-47), so it reflects creation order.
        assert names == ["Alpha", "Tango", "Zulu", "Mike"]


class TestAlphaSort:
    async def test_alpha_sort_interleaves_packages_and_diagrams(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_id = await _setup_mixed_set(client, h)

        # Switch the set to alphabetical sort.
        put_resp = await client.put(
            f"/api/sets/{set_id}",
            json={"name": "SortSet", "hierarchy_sort": "alpha"},
            headers=h,
        )
        assert put_resp.status_code == 200, put_resp.text
        assert put_resp.json()["hierarchy_sort"] == "alpha"

        names = await _names(client, h, set_id)
        # Pure alphabetical, no node-type tie-break.
        assert names == ["Alpha", "Mike", "Tango", "Zulu"]


class TestDateSort:
    async def test_newest_first(self, client: httpx.AsyncClient) -> None:
        h = await _auth(client)
        set_id = await _setup_mixed_set(client, h)
        await client.put(
            f"/api/sets/{set_id}",
            json={"name": "SortSet", "hierarchy_sort": "newest"},
            headers=h,
        )
        names = await _names(client, h, set_id)
        # Created in order: Zulu, Alpha, Mike, Tango → newest first
        # reverses that.
        assert names == ["Tango", "Mike", "Alpha", "Zulu"]

    async def test_oldest_first(self, client: httpx.AsyncClient) -> None:
        h = await _auth(client)
        set_id = await _setup_mixed_set(client, h)
        await client.put(
            f"/api/sets/{set_id}",
            json={"name": "SortSet", "hierarchy_sort": "oldest"},
            headers=h,
        )
        names = await _names(client, h, set_id)
        assert names == ["Zulu", "Alpha", "Mike", "Tango"]


class TestInvalidSort:
    async def test_rejects_unknown_sort_value(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_resp = await client.post(
            "/api/sets", json={"name": "X"}, headers=h,
        )
        set_id = set_resp.json()["id"]
        put_resp = await client.put(
            f"/api/sets/{set_id}",
            json={"name": "X", "hierarchy_sort": "bogus"},
            headers=h,
        )
        # Pydantic Literal rejects → 422.
        assert put_resp.status_code == 422


class TestSetResponse:
    async def test_get_set_returns_hierarchy_sort(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_resp = await client.post(
            "/api/sets", json={"name": "Y"}, headers=h,
        )
        set_id = set_resp.json()["id"]
        await client.put(
            f"/api/sets/{set_id}",
            json={"name": "Y", "hierarchy_sort": "alpha"},
            headers=h,
        )
        get_resp = await client.get(f"/api/sets/{set_id}", headers=h)
        assert get_resp.json()["hierarchy_sort"] == "alpha"
