"""v6.0.0 (ADR-164, SPEC-164-A): OAuth-issued access tokens flow through
the existing `get_current_user` dependency unchanged.

Three regressions to guard:
1. OAuth-issued JWT (with aud="iris-mcp", azp=client_id, role=...) passes
   `GET /api/auth/me`.
2. Legacy /api/auth/login JWT (no aud claim) still passes `GET /api/auth/me`.
3. PAT (iris_pat_*) still passes `GET /api/auth/me`.
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


async def _get_oauth_access_token(client: httpx.AsyncClient) -> str:
    """Run the full OAuth flow and return the access token."""
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
    return tok.json()["access_token"]


class TestOAuthJWTAcceptance:
    async def test_oauth_jwt_passes_get_current_user(
        self, client: httpx.AsyncClient,
    ) -> None:
        access_token = await _get_oauth_access_token(client)
        resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == "admin"

    async def test_legacy_login_jwt_still_passes(
        self, client: httpx.AsyncClient,
    ) -> None:
        await client.post(
            "/api/auth/setup",
            json={"username": "admin", "password": "AdminPass123!"},
        )
        login = await client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "AdminPass123!"},
        )
        legacy_jwt = login.json()["access_token"]
        resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {legacy_jwt}"},
        )
        assert resp.status_code == 200

    async def test_pat_still_passes(self, client: httpx.AsyncClient) -> None:
        await client.post(
            "/api/auth/setup",
            json={"username": "admin", "password": "AdminPass123!"},
        )
        login = await client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "AdminPass123!"},
        )
        jwt_token = login.json()["access_token"]
        pat_resp = await client.post(
            "/api/users/me/tokens",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json={"name": "test"},
        )
        pat = pat_resp.json()["token"]
        resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {pat}"},
        )
        assert resp.status_code == 200
