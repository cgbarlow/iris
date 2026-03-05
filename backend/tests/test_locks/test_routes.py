"""Integration tests for the edit locking system (ADR-080)."""

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


async def _auth_headers(
    client: httpx.AsyncClient,
    username: str = "admin",
    password: str = "AdminPass123!",
    *,
    setup: bool = True,
) -> dict[str, str]:
    """Setup user and return auth headers."""
    if setup:
        await client.post(
            "/api/auth/setup",
            json={"username": username, "password": password},
        )
    resp = await client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _create_second_user(
    client: httpx.AsyncClient, admin_headers: dict[str, str]
) -> dict[str, str]:
    """Create a second user and return their auth headers."""
    await client.post(
        "/api/users",
        json={"username": "user2", "password": "User2Pass123!", "role": "architect"},
        headers=admin_headers,
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "user2", "password": "User2Pass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestAcquireLock:
    @pytest.mark.anyio
    async def test_acquire_lock(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/locks",
            json={"target_type": "diagram", "target_id": "test-diagram-1"},
            headers=headers,
        )
        assert resp.status_code == 200
        lock = resp.json()
        assert lock["target_type"] == "diagram"
        assert lock["target_id"] == "test-diagram-1"
        assert lock["username"] == "admin"
        assert "id" in lock
        assert "expires_at" in lock

    @pytest.mark.anyio
    async def test_reacquire_own_lock_refreshes(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp1 = await client.post(
            "/api/locks",
            json={"target_type": "diagram", "target_id": "test-diagram-2"},
            headers=headers,
        )
        lock1 = resp1.json()

        resp2 = await client.post(
            "/api/locks",
            json={"target_type": "diagram", "target_id": "test-diagram-2"},
            headers=headers,
        )
        assert resp2.status_code == 200
        lock2 = resp2.json()
        assert lock2["id"] == lock1["id"]  # Same lock, refreshed

    @pytest.mark.anyio
    async def test_conflict_when_locked_by_another(self, client: httpx.AsyncClient) -> None:
        admin_headers = await _auth_headers(client)
        user2_headers = await _create_second_user(client, admin_headers)

        # Admin acquires lock
        await client.post(
            "/api/locks",
            json={"target_type": "diagram", "target_id": "contested-diagram"},
            headers=admin_headers,
        )

        # User2 tries to acquire same lock
        resp = await client.post(
            "/api/locks",
            json={"target_type": "diagram", "target_id": "contested-diagram"},
            headers=user2_headers,
        )
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert detail["lock"]["username"] == "admin"


class TestCheckLock:
    @pytest.mark.anyio
    async def test_check_unlocked(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get(
            "/api/locks/check?target_type=diagram&target_id=no-lock",
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["locked"] is False
        assert body["lock"] is None

    @pytest.mark.anyio
    async def test_check_locked_by_self(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await client.post(
            "/api/locks",
            json={"target_type": "element", "target_id": "elem-1"},
            headers=headers,
        )
        resp = await client.get(
            "/api/locks/check?target_type=element&target_id=elem-1",
            headers=headers,
        )
        body = resp.json()
        assert body["locked"] is True
        assert body["is_owner"] is True


class TestHeartbeat:
    @pytest.mark.anyio
    async def test_heartbeat_extends_lock(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        create_resp = await client.post(
            "/api/locks",
            json={"target_type": "diagram", "target_id": "hb-test"},
            headers=headers,
        )
        lock_id = create_resp.json()["id"]
        original_expires = create_resp.json()["expires_at"]

        hb_resp = await client.put(
            f"/api/locks/{lock_id}/heartbeat",
            headers=headers,
        )
        assert hb_resp.status_code == 200
        assert hb_resp.json()["expires_at"] >= original_expires

    @pytest.mark.anyio
    async def test_heartbeat_nonexistent_lock(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.put(
            "/api/locks/nonexistent-id/heartbeat",
            headers=headers,
        )
        assert resp.status_code == 404


class TestReleaseLock:
    @pytest.mark.anyio
    async def test_release_own_lock(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        create_resp = await client.post(
            "/api/locks",
            json={"target_type": "package", "target_id": "pkg-1"},
            headers=headers,
        )
        lock_id = create_resp.json()["id"]

        release_resp = await client.delete(
            f"/api/locks/{lock_id}",
            headers=headers,
        )
        assert release_resp.status_code == 204

        # Verify it's unlocked now
        check_resp = await client.get(
            "/api/locks/check?target_type=package&target_id=pkg-1",
            headers=headers,
        )
        assert check_resp.json()["locked"] is False

    @pytest.mark.anyio
    async def test_cannot_release_others_lock(self, client: httpx.AsyncClient) -> None:
        admin_headers = await _auth_headers(client)
        user2_headers = await _create_second_user(client, admin_headers)

        create_resp = await client.post(
            "/api/locks",
            json={"target_type": "diagram", "target_id": "others-lock"},
            headers=admin_headers,
        )
        lock_id = create_resp.json()["id"]

        # User2 tries to release admin's lock
        resp = await client.delete(
            f"/api/locks/{lock_id}",
            headers=user2_headers,
        )
        assert resp.status_code == 404  # "not found or not owned"


class TestExpiredLocks:
    @pytest.mark.anyio
    async def test_expired_lock_cleaned_on_acquire(self, client: httpx.AsyncClient) -> None:
        """Manually set a lock with past expires_at and verify it gets cleaned."""
        admin_headers = await _auth_headers(client)

        # Create a lock normally
        create_resp = await client.post(
            "/api/locks",
            json={"target_type": "diagram", "target_id": "expire-test"},
            headers=admin_headers,
        )
        lock_id = create_resp.json()["id"]

        # Manually expire the lock via direct DB access
        # (This simulates a lock that timed out)
        from app.database import DatabaseManager
        db = client._transport.app.state.db_manager.main_db  # type: ignore[attr-defined]
        await db.execute(
            "UPDATE edit_locks SET expires_at = '2000-01-01T00:00:00+00:00' WHERE id = ?",
            (lock_id,),
        )
        await db.commit()

        # Another user should now be able to acquire
        user2_headers = await _create_second_user(client, admin_headers)
        resp = await client.post(
            "/api/locks",
            json={"target_type": "diagram", "target_id": "expire-test"},
            headers=user2_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "user2"


class TestListLocks:
    @pytest.mark.anyio
    async def test_list_active_locks(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await client.post(
            "/api/locks",
            json={"target_type": "diagram", "target_id": "list-test-1"},
            headers=headers,
        )
        await client.post(
            "/api/locks",
            json={"target_type": "element", "target_id": "list-test-2"},
            headers=headers,
        )

        resp = await client.get("/api/locks", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 2


class TestAdminForceRelease:
    @pytest.mark.anyio
    async def test_admin_force_release(self, client: httpx.AsyncClient) -> None:
        admin_headers = await _auth_headers(client)
        user2_headers = await _create_second_user(client, admin_headers)

        # User2 acquires a lock
        create_resp = await client.post(
            "/api/locks",
            json={"target_type": "diagram", "target_id": "force-release-test"},
            headers=user2_headers,
        )
        lock_id = create_resp.json()["id"]

        # Admin force-releases it
        resp = await client.delete(
            f"/api/admin/locks/{lock_id}",
            headers=admin_headers,
        )
        assert resp.status_code == 204

        # Verify it's gone
        check_resp = await client.get(
            "/api/locks/check?target_type=diagram&target_id=force-release-test",
            headers=admin_headers,
        )
        assert check_resp.json()["locked"] is False

    @pytest.mark.anyio
    async def test_non_admin_cannot_force_release(self, client: httpx.AsyncClient) -> None:
        admin_headers = await _auth_headers(client)
        user2_headers = await _create_second_user(client, admin_headers)

        create_resp = await client.post(
            "/api/locks",
            json={"target_type": "diagram", "target_id": "no-force-test"},
            headers=admin_headers,
        )
        lock_id = create_resp.json()["id"]

        # User2 (architect role) tries to force-release
        resp = await client.delete(
            f"/api/admin/locks/{lock_id}",
            headers=user2_headers,
        )
        assert resp.status_code == 403
