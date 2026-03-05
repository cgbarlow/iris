"""Integration tests for bookmark routes."""

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
    db_manager = DatabaseManager(app_config.database)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as c:
        yield c
    await db_manager.close()


async def _admin_headers(client: httpx.AsyncClient) -> dict[str, str]:
    """Setup admin and return auth headers."""
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _create_diagram(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    name: str = "Test Diagram",
) -> str:
    """Create a diagram via the API and return its ID."""
    resp = await client.post(
        "/api/diagrams",
        json={"diagram_type": "simple", "name": name},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_package(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    name: str = "Test Package",
) -> str:
    """Create a package via the API and return its ID."""
    resp = await client.post(
        "/api/packages",
        json={"name": name},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestBookmarkDiagram:
    """Verify bookmarking a diagram."""

    async def test_bookmark_and_list(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        diagram_id = await _create_diagram(client, headers)

        # Bookmark a diagram
        resp = await client.post(
            f"/api/diagrams/{diagram_id}/bookmark", headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["diagram_id"] == diagram_id
        assert "created_at" in data

        # List bookmarks
        resp = await client.get("/api/bookmarks", headers=headers)
        assert resp.status_code == 200
        bookmarks = resp.json()
        assert len(bookmarks) == 1
        assert bookmarks[0]["diagram_id"] == diagram_id

    async def test_duplicate_bookmark_returns_409(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        diagram_id = await _create_diagram(client, headers)

        await client.post(
            f"/api/diagrams/{diagram_id}/bookmark", headers=headers,
        )
        resp = await client.post(
            f"/api/diagrams/{diagram_id}/bookmark", headers=headers,
        )
        assert resp.status_code == 409

    async def test_bookmark_requires_auth(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.post("/api/diagrams/some-id/bookmark")
        assert resp.status_code == 401


class TestUnbookmarkDiagram:
    """Verify unbookmarking a diagram."""

    async def test_unbookmark(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        diagram_id = await _create_diagram(client, headers)

        await client.post(
            f"/api/diagrams/{diagram_id}/bookmark", headers=headers,
        )
        resp = await client.delete(
            f"/api/diagrams/{diagram_id}/bookmark", headers=headers,
        )
        assert resp.status_code == 204

        # List should be empty
        resp = await client.get("/api/bookmarks", headers=headers)
        assert len(resp.json()) == 0

    async def test_unbookmark_not_found(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        resp = await client.delete(
            "/api/diagrams/nonexistent/bookmark", headers=headers,
        )
        assert resp.status_code == 404


class TestBookmarkIsolation:
    """Verify bookmarks are per-user."""

    async def test_bookmarks_are_per_user(
        self, client: httpx.AsyncClient,
    ) -> None:
        admin_headers = await _admin_headers(client)

        # Create two diagrams
        diagram_1 = await _create_diagram(client, admin_headers, "Diagram 1")
        diagram_2 = await _create_diagram(client, admin_headers, "Diagram 2")

        # Create a second user
        await client.post(
            "/api/users",
            json={
                "username": "viewer1",
                "password": "ViewerPass123!",
                "role": "viewer",
            },
            headers=admin_headers,
        )
        resp = await client.post(
            "/api/auth/login",
            json={"username": "viewer1", "password": "ViewerPass123!"},
        )
        viewer_headers = {
            "Authorization": f"Bearer {resp.json()['access_token']}",
        }

        # Admin bookmarks diagram_1
        await client.post(
            f"/api/diagrams/{diagram_1}/bookmark", headers=admin_headers,
        )
        # Viewer bookmarks diagram_2
        await client.post(
            f"/api/diagrams/{diagram_2}/bookmark", headers=viewer_headers,
        )

        # Each user only sees their own
        resp = await client.get("/api/bookmarks", headers=admin_headers)
        admin_bookmarks = resp.json()
        assert len(admin_bookmarks) == 1
        assert admin_bookmarks[0]["diagram_id"] == diagram_1

        resp = await client.get("/api/bookmarks", headers=viewer_headers)
        viewer_bookmarks = resp.json()
        assert len(viewer_bookmarks) == 1
        assert viewer_bookmarks[0]["diagram_id"] == diagram_2


class TestBookmarkPackage:
    """Verify bookmarking a package."""

    async def test_bookmark_package_and_list(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        package_id = await _create_package(client, headers)

        resp = await client.post(
            f"/api/packages/{package_id}/bookmark", headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["package_id"] == package_id
        assert data["diagram_id"] is None
        assert "created_at" in data

        resp = await client.get("/api/bookmarks", headers=headers)
        bookmarks = resp.json()
        assert len(bookmarks) == 1
        assert bookmarks[0]["package_id"] == package_id

    async def test_duplicate_package_bookmark_returns_409(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        package_id = await _create_package(client, headers)

        await client.post(
            f"/api/packages/{package_id}/bookmark", headers=headers,
        )
        resp = await client.post(
            f"/api/packages/{package_id}/bookmark", headers=headers,
        )
        assert resp.status_code == 409

    async def test_unbookmark_package(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        package_id = await _create_package(client, headers)

        await client.post(
            f"/api/packages/{package_id}/bookmark", headers=headers,
        )
        resp = await client.delete(
            f"/api/packages/{package_id}/bookmark", headers=headers,
        )
        assert resp.status_code == 204

        resp = await client.get("/api/bookmarks", headers=headers)
        assert len(resp.json()) == 0

    async def test_unbookmark_package_not_found(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        resp = await client.delete(
            "/api/packages/nonexistent/bookmark", headers=headers,
        )
        assert resp.status_code == 404

    async def test_mixed_diagram_and_package_bookmarks(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        diagram_id = await _create_diagram(client, headers)
        package_id = await _create_package(client, headers)

        await client.post(
            f"/api/diagrams/{diagram_id}/bookmark", headers=headers,
        )
        await client.post(
            f"/api/packages/{package_id}/bookmark", headers=headers,
        )

        resp = await client.get("/api/bookmarks", headers=headers)
        bookmarks = resp.json()
        assert len(bookmarks) == 2
        diagram_bms = [b for b in bookmarks if b["diagram_id"]]
        package_bms = [b for b in bookmarks if b["package_id"]]
        assert len(diagram_bms) == 1
        assert len(package_bms) == 1
