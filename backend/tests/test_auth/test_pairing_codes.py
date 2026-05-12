"""Integration tests for /api/auth/pairing-codes (ADR-160, SPEC-160-A).

Boots the FastAPI app with a temporary SQLite DB. Verifies the
pairing-code flow:

- create endpoint requires authentication
- create returns a typeable code + ISO-8601 expiry
- exchange endpoint is anonymous, one-shot, and returns a fresh PAT
- exchanged PAT authenticates against /api/auth/me
- subsequent exchange attempts for the same code return 410
- unknown / expired codes return 410
- per-user outstanding-code cap (>5) auto-purges oldest
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
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
        rate_limit_general=1000,
        rate_limit_pat=1000,
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


async def _setup_admin_jwt(client: httpx.AsyncClient) -> str:
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return resp.json()["access_token"]


class TestCreatePairingCode:
    async def test_create_requires_auth(self, client: httpx.AsyncClient) -> None:
        resp = await client.post("/api/auth/pairing-codes", json={})
        assert resp.status_code == 401

    async def test_create_returns_code_and_expiry(self, client: httpx.AsyncClient) -> None:
        jwt = await _setup_admin_jwt(client)
        resp = await client.post(
            "/api/auth/pairing-codes",
            headers={"Authorization": f"Bearer {jwt}"},
            json={},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["code"].startswith("IRIS-")
        assert "-" in body["code"][5:]
        assert len(body["code"]) == 14  # "IRIS-XXXX-YYYY"
        assert body["expires_at"]
        expires = datetime.fromisoformat(body["expires_at"])
        delta = expires - datetime.now(tz=UTC)
        assert timedelta(minutes=9) < delta <= timedelta(minutes=11)

    async def test_create_caps_outstanding_codes_per_user(
        self, client: httpx.AsyncClient,
    ) -> None:
        jwt = await _setup_admin_jwt(client)
        headers = {"Authorization": f"Bearer {jwt}"}
        codes: list[str] = []
        for _ in range(7):
            r = await client.post("/api/auth/pairing-codes", headers=headers, json={})
            codes.append(r.json()["code"])
        from app.config import AppConfig as _AppConfig  # noqa: PLC0415
        # Inspect the table directly via the running app's DB manager.
        db = client._transport.app.state.db_manager.main_db  # type: ignore[attr-defined]
        cursor = await db.execute(
            "SELECT COUNT(*) FROM pairing_codes WHERE exchanged_at IS NULL"
        )
        count = (await cursor.fetchone())[0]
        # Most-recent 5 should remain; the rest purged.
        assert count == 5, f"expected 5 outstanding codes, got {count}"
        assert isinstance(_AppConfig, type)  # silence unused-import lint


class TestExchangePairingCode:
    async def test_exchange_returns_pat(self, client: httpx.AsyncClient) -> None:
        jwt = await _setup_admin_jwt(client)
        create_resp = await client.post(
            "/api/auth/pairing-codes",
            headers={"Authorization": f"Bearer {jwt}"},
            json={},
        )
        code = create_resp.json()["code"]

        # Anonymous exchange.
        ex_resp = await client.post(f"/api/auth/pairing-codes/{code}/exchange")
        assert ex_resp.status_code == 200
        body = ex_resp.json()
        assert body["token"].startswith("iris_pat_")
        assert body["prefix"]
        assert body["expires_at"]
        assert body["mode"] == "pairing_code"

    async def test_exchanged_pat_authenticates(self, client: httpx.AsyncClient) -> None:
        jwt = await _setup_admin_jwt(client)
        create_resp = await client.post(
            "/api/auth/pairing-codes",
            headers={"Authorization": f"Bearer {jwt}"},
            json={},
        )
        code = create_resp.json()["code"]
        ex_resp = await client.post(f"/api/auth/pairing-codes/{code}/exchange")
        pat = ex_resp.json()["token"]

        me_resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {pat}"},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["username"] == "admin"

    async def test_exchange_is_one_shot(self, client: httpx.AsyncClient) -> None:
        jwt = await _setup_admin_jwt(client)
        create_resp = await client.post(
            "/api/auth/pairing-codes",
            headers={"Authorization": f"Bearer {jwt}"},
            json={},
        )
        code = create_resp.json()["code"]
        first = await client.post(f"/api/auth/pairing-codes/{code}/exchange")
        assert first.status_code == 200
        second = await client.post(f"/api/auth/pairing-codes/{code}/exchange")
        assert second.status_code == 410

    async def test_exchange_unknown_code_is_410(self, client: httpx.AsyncClient) -> None:
        resp = await client.post("/api/auth/pairing-codes/IRIS-AAAA-AAAA/exchange")
        assert resp.status_code == 410

    async def test_exchange_expired_code_is_410(
        self, client: httpx.AsyncClient,
    ) -> None:
        jwt = await _setup_admin_jwt(client)
        create_resp = await client.post(
            "/api/auth/pairing-codes",
            headers={"Authorization": f"Bearer {jwt}"},
            json={},
        )
        code = create_resp.json()["code"]

        # Force the row to be expired by overwriting expires_at.
        db = client._transport.app.state.db_manager.main_db  # type: ignore[attr-defined]
        past = (datetime.now(tz=UTC) - timedelta(minutes=1)).isoformat()
        await db.execute(
            "UPDATE pairing_codes SET expires_at = ? WHERE code = ?",
            (past, code),
        )
        await db.commit()

        resp = await client.post(f"/api/auth/pairing-codes/{code}/exchange")
        assert resp.status_code == 410

    async def test_exchange_accepts_lowercase_input(
        self, client: httpx.AsyncClient,
    ) -> None:
        jwt = await _setup_admin_jwt(client)
        create_resp = await client.post(
            "/api/auth/pairing-codes",
            headers={"Authorization": f"Bearer {jwt}"},
            json={},
        )
        code = create_resp.json()["code"]
        resp = await client.post(
            f"/api/auth/pairing-codes/{code.lower()}/exchange"
        )
        assert resp.status_code == 200
