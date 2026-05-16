"""v6.6.4 — `list_diagrams` gains `parent_package_id` filter.

Issue #133 follow-up. The MCP `list_diagrams` tool was the only way
an orient-sheet-driven assistant could discover root-level
(parent_package_id IS NULL) diagrams in a Set — but the backend
route was paginated to 50 rows ordered by `updated_at DESC` with no
parent filter, so once a Set crossed 50 diagrams and the
most-recently-touched ones lived under packages, the bracketing
root-level Introduction / Conclusion diagrams became unreachable
from the MCP surface.

Fix: `list_diagrams` (service + route + iris-client + MCP tool)
accepts `parent_package_id`. Three semantics:

- Omitted → no parent filter (return all, matches pre-v6.6.4
  behaviour).
- Literal string ``"null"`` → restrict to ``parent_package_id IS
  NULL`` (root-level only). The sentinel survives HTTP query
  strings and matches the orient instruction the model will read.
- A UUID string → restrict to ``parent_package_id = <uuid>``.

These tests cover the backend route end-to-end. iris-client
plumbing and MCP tool wiring have their own tests.

TDD: written before the route / service implementation.
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
    client: httpx.AsyncClient, headers: dict, name: str,
) -> str:
    resp = await client.post(
        "/api/sets", json={"name": name}, headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _create_package(
    client: httpx.AsyncClient,
    headers: dict,
    name: str,
    set_id: str,
) -> str:
    resp = await client.post(
        "/api/packages",
        json={"package_type": "uml", "name": name, "set_id": set_id},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _create_diagram(
    client: httpx.AsyncClient,
    headers: dict,
    name: str,
    set_id: str,
    parent_package_id: str | None = None,
) -> str:
    body: dict = {"diagram_type": "component", "name": name, "set_id": set_id}
    if parent_package_id:
        body["parent_package_id"] = parent_package_id
    resp = await client.post("/api/diagrams", json=body, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


class TestListDiagramsParentFilter:
    """Three semantics for `parent_package_id` on the list endpoint."""

    async def test_omitted_returns_all_diagrams_in_set(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers, "S")
        pkg_id = await _create_package(client, headers, "P", set_id)
        root_id = await _create_diagram(client, headers, "root", set_id)
        nested_id = await _create_diagram(
            client, headers, "nested", set_id, parent_package_id=pkg_id,
        )

        resp = await client.get(f"/api/diagrams?set_id={set_id}")
        assert resp.status_code == 200
        ids = {d["id"] for d in resp.json()["items"]}
        # Pre-v6.6.4 behaviour preserved when the param is omitted.
        assert root_id in ids
        assert nested_id in ids

    async def test_null_sentinel_returns_only_root_diagrams(
        self, client: httpx.AsyncClient,
    ) -> None:
        """The orient sheet instructs the model to call
        ``list_diagrams(set_id=..., parent_package_id=null)`` to find
        bracketing Introduction / Conclusion diagrams. The HTTP
        surface accepts the literal string ``"null"`` as that
        sentinel."""
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers, "S")
        pkg_id = await _create_package(client, headers, "P", set_id)
        root_id = await _create_diagram(client, headers, "root", set_id)
        nested_id = await _create_diagram(
            client, headers, "nested", set_id, parent_package_id=pkg_id,
        )

        resp = await client.get(
            f"/api/diagrams?set_id={set_id}&parent_package_id=null",
        )
        assert resp.status_code == 200
        ids = {d["id"] for d in resp.json()["items"]}
        assert root_id in ids
        assert nested_id not in ids

    async def test_specific_parent_returns_only_that_packages_children(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers, "S")
        pkg_a = await _create_package(client, headers, "A", set_id)
        pkg_b = await _create_package(client, headers, "B", set_id)
        in_a = await _create_diagram(
            client, headers, "in-a", set_id, parent_package_id=pkg_a,
        )
        in_b = await _create_diagram(
            client, headers, "in-b", set_id, parent_package_id=pkg_b,
        )
        root_id = await _create_diagram(client, headers, "root", set_id)

        resp = await client.get(
            f"/api/diagrams?set_id={set_id}&parent_package_id={pkg_a}",
        )
        assert resp.status_code == 200
        ids = {d["id"] for d in resp.json()["items"]}
        assert in_a in ids
        assert in_b not in ids
        assert root_id not in ids

    async def test_null_sentinel_survives_pagination_over_recent_edits(
        self, client: httpx.AsyncClient,
    ) -> None:
        """The bug the v6.6.4 fix targets. Pre-fix, a set with >50
        recently-edited under-package diagrams pushes the root-level
        ones off page 1 (the backend orders by ``updated_at DESC``
        with default ``page_size=50``). After the fix, filtering by
        ``parent_package_id=null`` returns the roots regardless of
        ordering noise."""
        headers = await _auth_headers(client)
        set_id = await _create_set(client, headers, "S")
        pkg_id = await _create_package(client, headers, "P", set_id)
        # The two bracketing root-level diagrams the orient sheet
        # cares about — created FIRST so they are the OLDEST
        # `updated_at` rows in the set.
        intro_id = await _create_diagram(client, headers, "intro", set_id)
        conclusion_id = await _create_diagram(
            client, headers, "conclusion", set_id,
        )
        # 50 fresher under-package diagrams that would push the roots
        # off page 1 under the default ordering.
        for i in range(50):
            await _create_diagram(
                client, headers, f"chap-{i:02d}", set_id,
                parent_package_id=pkg_id,
            )

        # Filtering — the roots come back in a single page even with
        # 52 diagrams in the set.
        resp = await client.get(
            f"/api/diagrams?set_id={set_id}&parent_package_id=null",
        )
        assert resp.status_code == 200
        body = resp.json()
        ids = {d["id"] for d in body["items"]}
        assert intro_id in ids
        assert conclusion_id in ids
        # Only the two roots are returned — no under-package leakage.
        assert body["total"] == 2
