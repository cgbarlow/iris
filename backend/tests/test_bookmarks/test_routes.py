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


async def _create_model(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    name: str = "Test Model",
) -> str:
    """Create a model via the API and return its ID."""
    resp = await client.post(
        "/api/models",
        json={"model_type": "simple", "name": name},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestBookmarkModel:
    """Verify bookmarking a model."""

    async def test_bookmark_and_list(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        model_id = await _create_model(client, headers)

        # Bookmark a model
        resp = await client.post(
            f"/api/models/{model_id}/bookmark", headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["model_id"] == model_id
        assert "created_at" in data

        # List bookmarks
        resp = await client.get("/api/bookmarks", headers=headers)
        assert resp.status_code == 200
        bookmarks = resp.json()
        assert len(bookmarks) == 1
        assert bookmarks[0]["model_id"] == model_id

    async def test_duplicate_bookmark_returns_409(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        model_id = await _create_model(client, headers)

        await client.post(
            f"/api/models/{model_id}/bookmark", headers=headers,
        )
        resp = await client.post(
            f"/api/models/{model_id}/bookmark", headers=headers,
        )
        assert resp.status_code == 409

    async def test_bookmark_requires_auth(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.post("/api/models/some-id/bookmark")
        assert resp.status_code == 401


class TestUnbookmarkModel:
    """Verify unbookmarking a model."""

    async def test_unbookmark(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        model_id = await _create_model(client, headers)

        await client.post(
            f"/api/models/{model_id}/bookmark", headers=headers,
        )
        resp = await client.delete(
            f"/api/models/{model_id}/bookmark", headers=headers,
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
            "/api/models/nonexistent/bookmark", headers=headers,
        )
        assert resp.status_code == 404


class TestBookmarkIsolation:
    """Verify bookmarks are per-user."""

    async def test_bookmarks_are_per_user(
        self, client: httpx.AsyncClient,
    ) -> None:
        admin_headers = await _admin_headers(client)

        # Create two models
        model_1 = await _create_model(client, admin_headers, "Model 1")
        model_2 = await _create_model(client, admin_headers, "Model 2")

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

        # Admin bookmarks model_1
        await client.post(
            f"/api/models/{model_1}/bookmark", headers=admin_headers,
        )
        # Viewer bookmarks model_2
        await client.post(
            f"/api/models/{model_2}/bookmark", headers=viewer_headers,
        )

        # Each user only sees their own
        resp = await client.get("/api/bookmarks", headers=admin_headers)
        admin_bookmarks = resp.json()
        assert len(admin_bookmarks) == 1
        assert admin_bookmarks[0]["model_id"] == model_1

        resp = await client.get("/api/bookmarks", headers=viewer_headers)
        viewer_bookmarks = resp.json()
        assert len(viewer_bookmarks) == 1
        assert viewer_bookmarks[0]["model_id"] == model_2
