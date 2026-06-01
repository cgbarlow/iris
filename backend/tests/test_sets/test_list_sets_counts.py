"""ADR-236: `list_sets` computes diagram/element/package counts with grouped
aggregate queries instead of per-set COUNT(*) loops. These tests pin the
behaviour that matters for that refactor — counts must be mapped to the
*correct* set (no cross-set leakage) and absent sets must read zero.
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
        transport=transport, base_url="http://test"
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
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _make_set(client: httpx.AsyncClient, headers: dict[str, str], name: str) -> str:
    return (await client.post("/api/sets", json={"name": name}, headers=headers)).json()["id"]


async def _make_package(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    set_id: str,
    name: str,
    parent_package_id: str | None = None,
) -> str:
    body: dict = {"name": name, "set_id": set_id}
    if parent_package_id is not None:
        body["parent_package_id"] = parent_package_id
    return (await client.post("/api/packages", json=body, headers=headers)).json()["id"]


async def _make_element(
    client: httpx.AsyncClient, headers: dict[str, str], set_id: str, name: str
) -> None:
    await client.post(
        "/api/elements",
        json={"element_type": "component", "name": name, "data": {}, "set_id": set_id},
        headers=headers,
    )


async def _make_diagram(
    client: httpx.AsyncClient, headers: dict[str, str], set_id: str, name: str
) -> None:
    await client.post(
        "/api/diagrams",
        json={"diagram_type": "simple-view", "name": name, "data": {}, "set_id": set_id},
        headers=headers,
    )


class TestListSetsCountIsolation:
    async def test_counts_mapped_to_correct_set(self, client: httpx.AsyncClient) -> None:
        """Set A is populated; set B is empty. Each set must report ITS OWN
        counts — a grouped query that mis-maps would leak A's counts onto B."""
        headers = await _auth_headers(client)
        set_a = await _make_set(client, headers, "Alpha")
        set_b = await _make_set(client, headers, "Bravo")

        # A: 2 packages (1 root + 1 child), 3 elements, 2 diagrams.
        root = await _make_package(client, headers, set_a, "Root A")
        await _make_package(client, headers, set_a, "Child A", parent_package_id=root)
        for i in range(3):
            await _make_element(client, headers, set_a, f"el-{i}")
        for i in range(2):
            await _make_diagram(client, headers, set_a, f"dg-{i}")

        items = (await client.get("/api/sets", headers=headers)).json()["items"]
        by_id = {i["id"]: i for i in items}

        a = by_id[set_a]
        assert a["package_count"] == 2
        assert a["package_count_root"] == 1
        assert a["element_count"] == 3
        assert a["diagram_count"] == 2

        b = by_id[set_b]
        assert b["package_count"] == 0
        assert b["package_count_root"] == 0
        assert b["element_count"] == 0
        assert b["diagram_count"] == 0

    async def test_collection_filtered_list_keeps_correct_counts(
        self, client: httpx.AsyncClient
    ) -> None:
        """The collection-filtered branch of list_sets must compute the same
        per-set counts as the unfiltered branch."""
        headers = await _auth_headers(client)
        coll = (
            await client.post("/api/collections", json={"name": "C"}, headers=headers)
        ).json()["id"]
        s = (
            await client.post(
                "/api/sets", json={"name": "InColl", "collection_id": coll}, headers=headers
            )
        ).json()["id"]
        await _make_element(client, headers, s, "only-el")

        items = (
            await client.get(f"/api/sets?collection_id={coll}", headers=headers)
        ).json()["items"]
        ours = next(i for i in items if i["id"] == s)
        assert ours["element_count"] == 1
        assert ours["diagram_count"] == 0
        assert ours["package_count"] == 0
