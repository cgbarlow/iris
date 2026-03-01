"""Tests for audit middleware."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from app.audit.service import verify_audit_chain
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
async def client_and_db(
    app_config: AppConfig,
) -> AsyncIterator[tuple[httpx.AsyncClient, DatabaseManager]]:
    application = create_app(app_config)
    db_manager = DatabaseManager(app_config.database)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as c:
        yield c, db_manager
    await db_manager.close()


async def _setup_and_login(
    client: httpx.AsyncClient,
) -> dict[str, str]:
    """Create admin via setup, login, return tokens."""
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return resp.json()


class TestAuditMiddleware:
    """Verify audit middleware records mutating requests."""

    async def test_post_request_creates_audit_entry(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, db_manager = client_and_db
        await _setup_and_login(client)

        cursor = await db_manager.audit_db.execute(
            "SELECT COUNT(*) FROM audit_log"
        )
        row = await cursor.fetchone()
        assert row[0] > 0

    async def test_get_request_not_audited(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, db_manager = client_and_db

        # Only GET requests
        await client.get("/health")

        cursor = await db_manager.audit_db.execute(
            "SELECT COUNT(*) FROM audit_log"
        )
        row = await cursor.fetchone()
        assert row[0] == 0

    async def test_audit_entry_contains_action(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, db_manager = client_and_db
        await _setup_and_login(client)

        cursor = await db_manager.audit_db.execute(
            "SELECT action FROM audit_log ORDER BY id LIMIT 1"
        )
        row = await cursor.fetchone()
        assert row[0] == "POST /api/auth/setup"

    async def test_audit_entry_has_ip_address(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, db_manager = client_and_db
        await _setup_and_login(client)

        cursor = await db_manager.audit_db.execute(
            "SELECT ip_address FROM audit_log ORDER BY id LIMIT 1"
        )
        row = await cursor.fetchone()
        assert row[0] is not None

    async def test_audit_chain_integrity(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, db_manager = client_and_db
        await _setup_and_login(client)
        is_valid, _count = await verify_audit_chain(db_manager.audit_db)
        assert is_valid


class TestAuditUsernameResolution:
    """Verify audit entries contain resolved username, not GUID (WP-6)."""

    async def test_audit_entry_contains_username_not_guid(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, db_manager = client_and_db
        tokens = await _setup_and_login(client)

        # Make an authenticated mutating request
        await client.post(
            "/api/entities",
            json={"entity_type": "service", "name": "Audit Test", "data": {}},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        cursor = await db_manager.audit_db.execute(
            "SELECT username FROM audit_log WHERE action = 'POST /api/entities'"
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "admin"

    async def test_audit_username_for_anonymous_request(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, db_manager = client_and_db

        # Unauthenticated POST (setup endpoint doesn't require auth)
        await client.post(
            "/api/auth/setup",
            json={"username": "admin", "password": "AdminPass123!"},
        )

        cursor = await db_manager.audit_db.execute(
            "SELECT username FROM audit_log WHERE action = 'POST /api/auth/setup'"
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "anonymous"
