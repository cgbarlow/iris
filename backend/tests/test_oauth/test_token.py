"""v6.0.0 (ADR-164, SPEC-164-A): POST /oauth/token — authorization_code
+ refresh_token grants with PKCE (RFC 7636).
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from typing import TYPE_CHECKING

import httpx
import pytest
from jose import jwt

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.main import create_app
from app.startup import initialize_databases

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path


JWT_SECRET = "test-secret-key-that-is-at-least-32-bytes-long-for-hs256"


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        debug=True,
        cors_origins=["http://localhost:5173"],
        database=DatabaseConfig(data_dir=str(tmp_path / "data")),
        auth=AuthConfig(
            jwt_secret=JWT_SECRET,
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


def _pkce_pair() -> tuple[str, str]:
    """Returns (code_verifier, code_challenge) for S256."""
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


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


async def _full_authorize_flow(
    client: httpx.AsyncClient,
    redirect_uri: str = "https://example.com/cb",
) -> tuple[str, str, str]:
    """Run the full prepare → decision=allow flow. Returns
    (client_id, code, code_verifier)."""
    jwt_token = await _setup_admin_jwt(client)
    verifier, challenge = _pkce_pair()
    reg = await client.post(
        "/oauth/register",
        json={
            "client_name": "Test client",
            "redirect_uris": [redirect_uri],
        },
    )
    client_id = reg.json()["client_id"]
    prep = await client.post(
        "/api/oauth/authorize/prepare",
        headers={"Authorization": f"Bearer {jwt_token}"},
        json={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
    )
    request_id = prep.json()["request_id"]
    dec = await client.post(
        "/api/oauth/authorize/decision",
        headers={"Authorization": f"Bearer {jwt_token}"},
        json={"request_id": request_id, "decision": "allow"},
    )
    redirect_to = dec.json()["redirect_to"]
    # code=... is between "?code=" and "&" or end.
    code = redirect_to.split("?code=")[1].split("&")[0]
    return client_id, code, verifier


class TestAuthorizationCodeGrant:
    async def test_happy_path_returns_tokens(
        self, client: httpx.AsyncClient,
    ) -> None:
        cid, code, verifier = await _full_authorize_flow(client)
        resp = await client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": cid,
                "redirect_uri": "https://example.com/cb",
                "code_verifier": verifier,
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["token_type"] == "Bearer"
        assert body["expires_in"] == 3600
        assert body["scope"] == "iris"
        assert body["access_token"]
        assert body["refresh_token"]

    async def test_access_token_is_a_valid_jwt(
        self, client: httpx.AsyncClient,
    ) -> None:
        cid, code, verifier = await _full_authorize_flow(client)
        resp = await client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": cid,
                "redirect_uri": "https://example.com/cb",
                "code_verifier": verifier,
            },
        )
        token = resp.json()["access_token"]
        # Decode (verify_aud=False to tolerate the "iris-mcp" aud claim).
        claims = jwt.decode(
            token, JWT_SECRET, algorithms=["HS256"],
            options={"verify_aud": False},
        )
        assert claims["sub"]
        assert claims["azp"] == cid
        assert claims["aud"] == "iris-mcp"
        assert claims["scope"] == "iris"
        assert claims["role"]  # required by get_current_user

    async def test_pkce_mismatch_returns_invalid_grant(
        self, client: httpx.AsyncClient,
    ) -> None:
        cid, code, _verifier = await _full_authorize_flow(client)
        resp = await client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": cid,
                "redirect_uri": "https://example.com/cb",
                "code_verifier": "wrong-verifier-that-doesnt-match",
            },
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["error"] == "invalid_grant"

    async def test_code_is_single_use(
        self, client: httpx.AsyncClient,
    ) -> None:
        cid, code, verifier = await _full_authorize_flow(client)
        # First exchange succeeds.
        r1 = await client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": cid,
                "redirect_uri": "https://example.com/cb",
                "code_verifier": verifier,
            },
        )
        assert r1.status_code == 200
        # Reuse fails.
        r2 = await client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": cid,
                "redirect_uri": "https://example.com/cb",
                "code_verifier": verifier,
            },
        )
        assert r2.status_code == 400
        assert r2.json()["detail"]["error"] == "invalid_grant"

    async def test_missing_pkce_verifier_400(
        self, client: httpx.AsyncClient,
    ) -> None:
        cid, code, _verifier = await _full_authorize_flow(client)
        resp = await client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": cid,
                "redirect_uri": "https://example.com/cb",
                # No code_verifier.
            },
        )
        assert resp.status_code == 400


class TestRefreshTokenGrant:
    async def test_refresh_rotation_issues_new_pair(
        self, client: httpx.AsyncClient,
    ) -> None:
        cid, code, verifier = await _full_authorize_flow(client)
        first = await client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": cid,
                "redirect_uri": "https://example.com/cb",
                "code_verifier": verifier,
            },
        )
        first_refresh = first.json()["refresh_token"]

        rotated = await client.post(
            "/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": cid,
                "refresh_token": first_refresh,
            },
        )
        assert rotated.status_code == 200, rotated.text
        body = rotated.json()
        assert body["access_token"]
        assert body["refresh_token"]
        assert body["refresh_token"] != first_refresh

    async def test_reused_refresh_revokes_family(
        self, client: httpx.AsyncClient,
    ) -> None:
        cid, code, verifier = await _full_authorize_flow(client)
        first = await client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": cid,
                "redirect_uri": "https://example.com/cb",
                "code_verifier": verifier,
            },
        )
        first_refresh = first.json()["refresh_token"]
        # Rotate once to get a new pair.
        rot = await client.post(
            "/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": cid,
                "refresh_token": first_refresh,
            },
        )
        second_refresh = rot.json()["refresh_token"]
        # Re-presenting first_refresh (now used) MUST be rejected AND
        # revoke the family (so second_refresh also stops working).
        replay = await client.post(
            "/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": cid,
                "refresh_token": first_refresh,
            },
        )
        assert replay.status_code == 400
        # second_refresh is now in a revoked family.
        replay2 = await client.post(
            "/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": cid,
                "refresh_token": second_refresh,
            },
        )
        assert replay2.status_code == 400

    async def test_cross_client_refresh_rejected(
        self, client: httpx.AsyncClient,
    ) -> None:
        cid_a, code, verifier = await _full_authorize_flow(client)
        first = await client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": cid_a,
                "redirect_uri": "https://example.com/cb",
                "code_verifier": verifier,
            },
        )
        refresh = first.json()["refresh_token"]
        # Different client tries to use A's refresh token.
        reg_b = await client.post(
            "/oauth/register",
            json={
                "client_name": "Other client",
                "redirect_uris": ["https://b.example/cb"],
            },
        )
        cid_b = reg_b.json()["client_id"]
        resp = await client.post(
            "/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": cid_b,
                "refresh_token": refresh,
            },
        )
        assert resp.status_code == 400


class TestUnsupportedGrant:
    async def test_unknown_grant_type_returns_400(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.post(
            "/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": "irrelevant",
            },
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["error"] == "unsupported_grant_type"
