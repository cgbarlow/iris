"""v6.0.0 (ADR-164, SPEC-164-A): POST /oauth/revoke — RFC 7009.
Marks a refresh token revoked. Always 200 per spec.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
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


async def _get_refresh_token(client: httpx.AsyncClient) -> tuple[str, str]:
    """Run the full flow and return (client_id, refresh_token)."""
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    login = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    jwt_token = login.json()["access_token"]

    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest(),
    ).rstrip(b"=").decode("ascii")

    reg = await client.post(
        "/oauth/register",
        json={
            "client_name": "Test",
            "redirect_uris": ["https://example.com/cb"],
        },
    )
    cid = reg.json()["client_id"]
    prep = await client.post(
        "/api/oauth/authorize/prepare",
        headers={"Authorization": f"Bearer {jwt_token}"},
        json={
            "response_type": "code",
            "client_id": cid,
            "redirect_uri": "https://example.com/cb",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
    )
    dec = await client.post(
        "/api/oauth/authorize/decision",
        headers={"Authorization": f"Bearer {jwt_token}"},
        json={"request_id": prep.json()["request_id"], "decision": "allow"},
    )
    code = dec.json()["redirect_to"].split("?code=")[1].split("&")[0]
    tok = await client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": cid,
            "redirect_uri": "https://example.com/cb",
            "code_verifier": verifier,
        },
    )
    return cid, tok.json()["refresh_token"]


class TestRevoke:
    async def test_revoke_returns_200(self, client: httpx.AsyncClient) -> None:
        cid, refresh = await _get_refresh_token(client)
        resp = await client.post(
            "/oauth/revoke",
            data={"client_id": cid, "token": refresh},
        )
        assert resp.status_code == 200

    async def test_revoked_token_cannot_refresh(
        self, client: httpx.AsyncClient,
    ) -> None:
        cid, refresh = await _get_refresh_token(client)
        await client.post(
            "/oauth/revoke",
            data={"client_id": cid, "token": refresh},
        )
        resp = await client.post(
            "/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": cid,
                "refresh_token": refresh,
            },
        )
        assert resp.status_code == 400

    async def test_revoke_unknown_token_still_200(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.post(
            "/oauth/revoke",
            data={"client_id": "iris-mcp-x", "token": "bogus"},
        )
        # RFC 7009: always 200, regardless of whether the token existed.
        assert resp.status_code == 200
