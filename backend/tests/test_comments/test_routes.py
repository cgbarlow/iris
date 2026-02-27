"""Integration tests for comment CRUD routes."""

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


async def _create_viewer_headers(
    client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    username: str = "viewer1",
) -> dict[str, str]:
    """Create a viewer user and return auth headers."""
    await client.post(
        "/api/users",
        json={
            "username": username,
            "password": "ViewerPass123!",
            "role": "viewer",
        },
        headers=admin_headers,
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": username, "password": "ViewerPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestEntityComments:
    """Verify comments on entities."""

    async def test_list_empty_comments(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        resp = await client.get(
            "/api/entities/some-entity-id/comments", headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_create_and_list_entity_comment(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        # Create a comment
        resp = await client.post(
            "/api/entities/ent-1/comments",
            json={"content": "This is a test comment."},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "This is a test comment."
        assert data["target_type"] == "entity"
        assert data["target_id"] == "ent-1"
        assert "id" in data
        assert "created_at" in data

        # List comments
        resp = await client.get(
            "/api/entities/ent-1/comments", headers=headers,
        )
        assert resp.status_code == 200
        comments = resp.json()
        assert len(comments) == 1
        assert comments[0]["content"] == "This is a test comment."

    async def test_create_requires_auth(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.post(
            "/api/entities/ent-1/comments",
            json={"content": "No auth"},
        )
        assert resp.status_code == 401


class TestModelComments:
    """Verify comments on models."""

    async def test_create_and_list_model_comment(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        resp = await client.post(
            "/api/models/model-1/comments",
            json={"content": "Model feedback."},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["target_type"] == "model"
        assert resp.json()["target_id"] == "model-1"

        resp = await client.get(
            "/api/models/model-1/comments", headers=headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1


class TestUpdateComment:
    """Verify comment updates."""

    async def test_update_own_comment(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        create_resp = await client.post(
            "/api/entities/ent-1/comments",
            json={"content": "Original content."},
            headers=headers,
        )
        comment_id = create_resp.json()["id"]

        resp = await client.put(
            f"/api/comments/{comment_id}",
            json={"content": "Updated content."},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == "Updated content."

    async def test_update_nonexistent_returns_404(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        resp = await client.put(
            "/api/comments/nonexistent",
            json={"content": "Nope."},
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_update_other_users_comment_forbidden(
        self, client: httpx.AsyncClient,
    ) -> None:
        admin_headers = await _admin_headers(client)
        viewer_headers = await _create_viewer_headers(
            client, admin_headers,
        )
        # Viewer creates a comment
        create_resp = await client.post(
            "/api/entities/ent-1/comments",
            json={"content": "Viewer comment."},
            headers=viewer_headers,
        )
        comment_id = create_resp.json()["id"]

        # Create another viewer who tries to edit it
        other_headers = await _create_viewer_headers(
            client, admin_headers, username="viewer2",
        )
        resp = await client.put(
            f"/api/comments/{comment_id}",
            json={"content": "Hijacked!"},
            headers=other_headers,
        )
        assert resp.status_code == 403

    async def test_admin_can_update_any_comment(
        self, client: httpx.AsyncClient,
    ) -> None:
        admin_headers = await _admin_headers(client)
        viewer_headers = await _create_viewer_headers(
            client, admin_headers,
        )
        create_resp = await client.post(
            "/api/entities/ent-1/comments",
            json={"content": "Viewer wrote this."},
            headers=viewer_headers,
        )
        comment_id = create_resp.json()["id"]

        resp = await client.put(
            f"/api/comments/{comment_id}",
            json={"content": "Admin edited this."},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == "Admin edited this."


class TestDeleteComment:
    """Verify comment soft-deletion."""

    async def test_delete_own_comment(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        create_resp = await client.post(
            "/api/entities/ent-1/comments",
            json={"content": "To be deleted."},
            headers=headers,
        )
        comment_id = create_resp.json()["id"]

        resp = await client.delete(
            f"/api/comments/{comment_id}", headers=headers,
        )
        assert resp.status_code == 204

        # Deleted comment should not appear in listing
        resp = await client.get(
            "/api/entities/ent-1/comments", headers=headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    async def test_delete_nonexistent_returns_404(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        resp = await client.delete(
            "/api/comments/nonexistent", headers=headers,
        )
        assert resp.status_code == 404

    async def test_delete_other_users_comment_forbidden(
        self, client: httpx.AsyncClient,
    ) -> None:
        admin_headers = await _admin_headers(client)
        viewer_headers = await _create_viewer_headers(
            client, admin_headers,
        )
        create_resp = await client.post(
            "/api/entities/ent-1/comments",
            json={"content": "Protected."},
            headers=viewer_headers,
        )
        comment_id = create_resp.json()["id"]

        other_headers = await _create_viewer_headers(
            client, admin_headers, username="viewer2",
        )
        resp = await client.delete(
            f"/api/comments/{comment_id}", headers=other_headers,
        )
        assert resp.status_code == 403

    async def test_admin_can_delete_any_comment(
        self, client: httpx.AsyncClient,
    ) -> None:
        admin_headers = await _admin_headers(client)
        viewer_headers = await _create_viewer_headers(
            client, admin_headers,
        )
        create_resp = await client.post(
            "/api/entities/ent-1/comments",
            json={"content": "Viewer comment."},
            headers=viewer_headers,
        )
        comment_id = create_resp.json()["id"]

        resp = await client.delete(
            f"/api/comments/{comment_id}", headers=admin_headers,
        )
        assert resp.status_code == 204


class TestCommentValidation:
    """Verify input validation."""

    async def test_empty_content_rejected(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        resp = await client.post(
            "/api/entities/ent-1/comments",
            json={"content": ""},
            headers=headers,
        )
        assert resp.status_code == 422
