"""Tests for PNG thumbnail generation and startup regeneration (ADR-032)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.main import create_app
from app.models_crud.thumbnail import (
    THEME_COLORS,
    VALID_THEMES,
    get_thumbnail,
    regenerate_all_thumbnails,
)
from app.startup import initialize_databases

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path

    import aiosqlite

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

_MODELS_INSERT = (
    "INSERT INTO models "
    "(id, model_type, current_version, created_at, created_by, updated_at) "
    "VALUES (?, 'simple-view', 1, ?, ?, ?)"
)

_MODELS_INSERT_DELETED = (
    "INSERT INTO models "
    "(id, model_type, current_version, "
    "created_at, created_by, updated_at, is_deleted) "
    "VALUES (?, 'simple-view', 1, ?, ?, ?, 1)"
)

_VERSIONS_INSERT = (
    "INSERT INTO model_versions "
    "(model_id, version, name, description, data, "
    "change_type, created_at, created_by) "
    "VALUES (?, 1, ?, NULL, ?, 'create', ?, ?)"
)

_THUMBS_INSERT = (
    "INSERT OR REPLACE INTO model_thumbnails "
    "(model_id, theme, thumbnail, updated_at) VALUES (?, ?, ?, ?)"
)


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
async def client(
    app_config: AppConfig,
) -> AsyncIterator[httpx.AsyncClient]:
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


async def _auth_headers(
    client: httpx.AsyncClient,
) -> dict[str, str]:
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


def _node_data(label: str = "T") -> str:
    """Return JSON model data with one node."""
    return json.dumps({
        "nodes": [
            {"id": "n1", "position": {"x": 0, "y": 0}, "data": {"label": label}}
        ],
    })


async def _insert_test_user(
    db: aiosqlite.Connection,
) -> str:
    """Insert a test user and return the user ID."""
    user_id = "test-user-id"
    cursor = await db.execute(
        "SELECT id FROM users WHERE id = ?", (user_id,),
    )
    if await cursor.fetchone():
        return user_id
    cursor = await db.execute(
        "SELECT id FROM roles WHERE name = 'Viewer'",
    )
    role_row = await cursor.fetchone()
    role_id = role_row[0] if role_row else "viewer"
    await db.execute(
        "INSERT INTO users (id, username, password_hash, role) "
        "VALUES (?, ?, ?, ?)",
        (user_id, "testuser", "not-a-real-hash", role_id),
    )
    await db.commit()
    return user_id


class TestThumbnailEndpoint:
    """Verify thumbnail endpoint returns valid PNG."""

    async def test_thumbnail_returns_200_after_create(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/models",
            json={
                "model_type": "simple-view",
                "name": "PNG Test",
                "data": {
                    "nodes": [
                        {"id": "n1", "position": {"x": 0, "y": 0},
                         "data": {"label": "A"}},
                        {"id": "n2", "position": {"x": 100, "y": 100},
                         "data": {"label": "B"}},
                    ],
                    "edges": [{"source": "n1", "target": "n2"}],
                },
            },
            headers=headers,
        )
        assert resp.status_code == 201
        model_id = resp.json()["id"]

        thumb = await client.get(
            f"/api/models/{model_id}/thumbnail",
        )
        assert thumb.status_code == 200

    async def test_thumbnail_has_png_content_type(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/models",
            json={
                "model_type": "simple-view",
                "name": "PNG Type Test",
                "data": json.loads(_node_data("X")),
            },
            headers=headers,
        )
        model_id = resp.json()["id"]

        thumb = await client.get(
            f"/api/models/{model_id}/thumbnail",
        )
        assert thumb.headers["content-type"] == "image/png"

    async def test_thumbnail_has_png_magic_bytes(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/models",
            json={
                "model_type": "simple-view",
                "name": "PNG Magic Test",
                "data": json.loads(_node_data("M")),
            },
            headers=headers,
        )
        model_id = resp.json()["id"]

        thumb = await client.get(
            f"/api/models/{model_id}/thumbnail",
        )
        assert thumb.content[:8] == PNG_MAGIC

    async def test_thumbnail_nonexistent_model_returns_404(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.get(
            "/api/models/nonexistent-id/thumbnail",
        )
        assert resp.status_code == 404


class TestRegenerateAllThumbnails:
    """Verify regenerate_all_thumbnails creates entries."""

    async def test_creates_thumbnails_for_models_without_entries(
        self, app_config: AppConfig,
    ) -> None:
        """Models without thumbnails get PNG after regeneration."""
        db_manager = DatabaseManager(app_config.database)
        await initialize_databases(db_manager)
        db = db_manager.main_db

        user_id = await _insert_test_user(db)
        model_id = "test-model-no-thumb"
        now = datetime.now(tz=UTC).isoformat()

        await db.execute(
            _MODELS_INSERT, (model_id, now, user_id, now),
        )
        await db.execute(
            _VERSIONS_INSERT,
            (model_id, "Test", _node_data(), now, user_id),
        )
        await db.commit()

        # Remove any startup-generated thumbnail
        await db.execute(
            "DELETE FROM model_thumbnails WHERE model_id = ?",
            (model_id,),
        )
        await db.commit()

        thumb = await get_thumbnail(db, model_id)
        assert thumb is None

        await regenerate_all_thumbnails(db)

        thumb = await get_thumbnail(db, model_id)
        assert thumb is not None
        assert thumb[:8] == PNG_MAGIC

        await db_manager.close()

    async def test_updates_stale_svg_thumbnails_to_png(
        self, app_config: AppConfig,
    ) -> None:
        """SVG-byte thumbnails are replaced with PNG."""
        db_manager = DatabaseManager(app_config.database)
        await initialize_databases(db_manager)
        db = db_manager.main_db

        user_id = await _insert_test_user(db)
        model_id = "test-model-svg-thumb"
        now = datetime.now(tz=UTC).isoformat()

        await db.execute(
            _MODELS_INSERT, (model_id, now, user_id, now),
        )
        await db.execute(
            _VERSIONS_INSERT,
            (model_id, "SVG Test", _node_data("S"), now, user_id),
        )
        # Overwrite with stale SVG bytes
        await db.execute(
            _THUMBS_INSERT,
            (model_id, "dark", b"<svg>stale</svg>", now),
        )
        await db.commit()

        thumb_before = await get_thumbnail(db, model_id)
        assert thumb_before is not None
        assert thumb_before[:8] != PNG_MAGIC

        await regenerate_all_thumbnails(db)

        thumb_after = await get_thumbnail(db, model_id)
        assert thumb_after is not None
        assert thumb_after[:8] == PNG_MAGIC

        await db_manager.close()

    async def test_skips_deleted_models(
        self, app_config: AppConfig,
    ) -> None:
        """Deleted models should not get thumbnails."""
        db_manager = DatabaseManager(app_config.database)
        await initialize_databases(db_manager)
        db = db_manager.main_db

        user_id = await _insert_test_user(db)
        model_id = "test-model-deleted"
        now = datetime.now(tz=UTC).isoformat()

        await db.execute(
            _MODELS_INSERT_DELETED,
            (model_id, now, user_id, now),
        )
        await db.execute(
            _VERSIONS_INSERT,
            (model_id, "Deleted", json.dumps({"nodes": []}), now, user_id),
        )
        await db.commit()

        await regenerate_all_thumbnails(db)

        thumb = await get_thumbnail(db, model_id)
        assert thumb is None

        await db_manager.close()


class TestStartupThumbnailRegeneration:
    """Verify thumbnails are regenerated on startup."""

    async def test_startup_creates_thumbnails(
        self, app_config: AppConfig,
    ) -> None:
        """After restart, all models have PNG thumbnails."""
        db_manager = DatabaseManager(app_config.database)
        await initialize_databases(db_manager)
        db = db_manager.main_db

        user_id = await _insert_test_user(db)
        model_id = "startup-test-model"
        now = datetime.now(tz=UTC).isoformat()

        await db.execute(
            _MODELS_INSERT, (model_id, now, user_id, now),
        )
        await db.execute(
            _VERSIONS_INSERT,
            (model_id, "Startup", _node_data("S"), now, user_id),
        )
        await db.commit()
        await db_manager.close()

        # Re-initialize (simulates restart)
        db_manager2 = DatabaseManager(app_config.database)
        await initialize_databases(db_manager2)

        thumb = await get_thumbnail(db_manager2.main_db, model_id)
        assert thumb is not None
        assert thumb[:8] == PNG_MAGIC

        await db_manager2.close()


class TestThemeThumbnails:
    """Verify theme-aware thumbnail generation (WP-1)."""

    async def test_thumbnail_endpoint_accepts_theme_param(
        self, client: httpx.AsyncClient,
    ) -> None:
        """Thumbnail endpoint returns 200 with ?theme=light."""
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/models",
            json={
                "model_type": "simple-view",
                "name": "Theme Light Test",
                "data": json.loads(_node_data("L")),
            },
            headers=headers,
        )
        assert resp.status_code == 201
        model_id = resp.json()["id"]

        thumb = await client.get(
            f"/api/models/{model_id}/thumbnail?theme=light",
        )
        assert thumb.status_code == 200
        assert thumb.content[:8] == PNG_MAGIC

    async def test_thumbnail_endpoint_accepts_high_contrast(
        self, client: httpx.AsyncClient,
    ) -> None:
        """Thumbnail endpoint returns 200 with ?theme=high-contrast."""
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/models",
            json={
                "model_type": "simple-view",
                "name": "Theme HC Test",
                "data": json.loads(_node_data("H")),
            },
            headers=headers,
        )
        assert resp.status_code == 201
        model_id = resp.json()["id"]

        thumb = await client.get(
            f"/api/models/{model_id}/thumbnail?theme=high-contrast",
        )
        assert thumb.status_code == 200
        assert thumb.content[:8] == PNG_MAGIC

    async def test_regeneration_creates_all_three_theme_variants(
        self, app_config: AppConfig,
    ) -> None:
        """After regeneration each model has dark, light, and high-contrast thumbnails."""
        db_manager = DatabaseManager(app_config.database)
        await initialize_databases(db_manager)
        db = db_manager.main_db

        user_id = await _insert_test_user(db)
        model_id = "test-model-themes"
        now = datetime.now(tz=UTC).isoformat()

        await db.execute(
            _MODELS_INSERT, (model_id, now, user_id, now),
        )
        await db.execute(
            _VERSIONS_INSERT,
            (model_id, "Theme", _node_data("T"), now, user_id),
        )
        await db.commit()

        # Clear any existing thumbnails for this model
        await db.execute(
            "DELETE FROM model_thumbnails WHERE model_id = ?",
            (model_id,),
        )
        await db.commit()

        await regenerate_all_thumbnails(db)

        for theme in VALID_THEMES:
            thumb = await get_thumbnail(db, model_id, theme=theme)
            assert thumb is not None, f"Missing thumbnail for theme={theme}"
            assert thumb[:8] == PNG_MAGIC, f"Not PNG for theme={theme}"

        await db_manager.close()

    async def test_theme_colors_has_three_entries(self) -> None:
        """THEME_COLORS dict contains exactly 3 themes."""
        assert len(THEME_COLORS) == 3
        assert set(THEME_COLORS.keys()) == {"light", "dark", "high-contrast"}

    async def test_default_theme_is_dark(
        self, client: httpx.AsyncClient,
    ) -> None:
        """Requesting without ?theme defaults to dark."""
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/models",
            json={
                "model_type": "simple-view",
                "name": "Default Theme Test",
                "data": json.loads(_node_data("D")),
            },
            headers=headers,
        )
        model_id = resp.json()["id"]

        thumb_default = await client.get(
            f"/api/models/{model_id}/thumbnail",
        )
        thumb_dark = await client.get(
            f"/api/models/{model_id}/thumbnail?theme=dark",
        )
        assert thumb_default.status_code == 200
        assert thumb_dark.status_code == 200
        assert thumb_default.content == thumb_dark.content


class TestAdminThumbnailRegeneration:
    """Verify admin thumbnail regeneration endpoint (WP-9)."""

    async def test_regeneration_endpoint_returns_200_and_count(
        self, client: httpx.AsyncClient,
    ) -> None:
        """Admin can trigger regeneration and gets back a count."""
        headers = await _auth_headers(client)
        # Create a model so there is something to regenerate
        await client.post(
            "/api/models",
            json={
                "model_type": "simple-view",
                "name": "Regen Test",
                "data": json.loads(_node_data("R")),
            },
            headers=headers,
        )

        resp = await client.post(
            "/api/admin/thumbnails/regenerate",
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "count" in body
        assert body["count"] >= 1

    async def test_non_admin_gets_403(
        self, client: httpx.AsyncClient,
    ) -> None:
        """Non-admin users are forbidden from triggering regeneration."""
        admin_headers = await _auth_headers(client)
        # Create a non-admin user
        await client.post(
            "/api/users",
            json={
                "username": "viewer_user",
                "password": "ViewerPass123!",
                "role": "viewer",
            },
            headers=admin_headers,
        )
        # Login as the non-admin user
        login_resp = await client.post(
            "/api/auth/login",
            json={"username": "viewer_user", "password": "ViewerPass123!"},
        )
        viewer_headers = {
            "Authorization": f"Bearer {login_resp.json()['access_token']}",
        }

        resp = await client.post(
            "/api/admin/thumbnails/regenerate",
            headers=viewer_headers,
        )
        assert resp.status_code == 403
