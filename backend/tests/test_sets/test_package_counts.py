"""ADR-158 / v5.13.0: Set responses include `package_count` and
`package_count_root` so MCP clients see structural breadth without
needing to paginate `list_packages` to discover scope.
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


class TestPackageCountsOnGetSet:
    async def test_empty_set_has_zero_counts(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s = (await client.post("/api/sets", json={"name": "empty"}, headers=headers)).json()

        resp = await client.get(f"/api/sets/{s['id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["package_count"] == 0
        assert body["package_count_root"] == 0

    async def test_counts_root_packages_only_at_root_field(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        s = (await client.post("/api/sets", json={"name": "tree"}, headers=headers)).json()

        # 3 root packages + 2 children = 5 total, 3 root.
        roots = []
        for name in ("Chapter A", "Chapter B", "Chapter C"):
            r = (await client.post(
                "/api/packages",
                json={"name": name, "set_id": s["id"]},
                headers=headers,
            )).json()
            roots.append(r["id"])

        # Two children under Chapter A.
        for name in ("A.1", "A.2"):
            await client.post(
                "/api/packages",
                json={"name": name, "set_id": s["id"], "parent_package_id": roots[0]},
                headers=headers,
            )

        resp = await client.get(f"/api/sets/{s['id']}")
        body = resp.json()
        assert body["package_count"] == 5
        assert body["package_count_root"] == 3

    async def test_list_sets_includes_package_counts(
        self, client: httpx.AsyncClient,
    ) -> None:
        """The list endpoint must populate the new fields too — the MCP
        get_set tool returns this shape, but list_sets is the broader
        catalogue and matters for navigation."""
        headers = await _auth_headers(client)
        s = (await client.post(
            "/api/sets", json={"name": "listed"}, headers=headers,
        )).json()
        await client.post(
            "/api/packages",
            json={"name": "Only Root", "set_id": s["id"]},
            headers=headers,
        )

        resp = await client.get("/api/sets")
        items = resp.json()["items"]
        ours = next(i for i in items if i["id"] == s["id"])
        assert ours["package_count"] == 1
        assert ours["package_count_root"] == 1

    async def test_create_response_initialises_counts_to_zero(
        self, client: httpx.AsyncClient,
    ) -> None:
        """The create endpoint also must populate these so client code
        that uses the create response doesn't see KeyError."""
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/sets", json={"name": "fresh"}, headers=headers,
        )
        body = resp.json()
        assert body["package_count"] == 0
        assert body["package_count_root"] == 0

    async def test_soft_deleted_packages_excluded(
        self, client: httpx.AsyncClient,
    ) -> None:
        """Counts must reflect live state, not historic. The DELETE
        endpoint requires `If-Match: <version>` header for optimistic
        concurrency."""
        headers = await _auth_headers(client)
        s = (await client.post(
            "/api/sets", json={"name": "delete-test"}, headers=headers,
        )).json()
        p = (await client.post(
            "/api/packages",
            json={"name": "to-delete", "set_id": s["id"]},
            headers=headers,
        )).json()
        delete_resp = await client.delete(
            f"/api/packages/{p['id']}",
            headers={**headers, "If-Match": str(p["current_version"])},
        )
        assert delete_resp.status_code == 204

        body = (await client.get(f"/api/sets/{s['id']}")).json()
        assert body["package_count"] == 0
        assert body["package_count_root"] == 0
