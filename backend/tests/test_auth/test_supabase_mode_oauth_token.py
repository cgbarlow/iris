"""v6.0.14 (ADR-174): in Supabase deployment mode, `get_current_user`
must accept iris-OAuth-issued tokens (signed with IRIS_JWT_SECRET,
`aud="iris-mcp"`) in addition to Supabase-issued tokens. Without this
hybrid validation, every OAuth bearer 401'd in production because
Supabase JWKS / SUPABASE_JWT_SECRET never matches the iris JWT secret.

These tests pin the routing: tokens with `aud="iris-mcp"` go through
iris's HS256 validator using `config.auth.jwt_secret`; everything else
goes through `decode_supabase_jwt`.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from jose import jwt

from app.auth.dependencies import _get_current_user_supabase
from app.config import AppConfig, AuthConfig, DatabaseConfig, SupabaseConfig


def _make_iris_oauth_token(jwt_secret: str, user_id: str = "user-abc") -> str:
    """Mint an iris-OAuth-shaped JWT for testing.

    Mirrors the claim set produced by `oauth_service.issue_access_token`.
    """
    payload = {
        "sub": user_id,
        "role": "viewer",
        "aud": "iris-mcp",
        "azp": "iris-mcp-test-client",
        "scope": "iris",
        "jti": "test-jti-12345",
    }
    return jwt.encode(payload, jwt_secret, algorithm="HS256")


def _make_supabase_shaped_token(
    jwt_secret: str, user_id: str = "user-xyz",
) -> str:
    """Mint a Supabase-shaped JWT (no aud=iris-mcp; signed with the
    Supabase jwt_secret in this test). The hybrid validator should
    treat this as a Supabase token."""
    payload = {
        "sub": user_id,
        "aud": "authenticated",
        "role": "authenticated",
    }
    return jwt.encode(payload, jwt_secret, algorithm="HS256")


def _fake_request(config: AppConfig) -> Any:
    """Build a minimal Request stand-in carrying the app state."""
    class _State:
        pass

    class _AppState:
        def __init__(self) -> None:
            self.config = config
            self.db_manager = _DBManager()

    class _DBManager:
        def __init__(self) -> None:
            self.main_db = None  # get_profile mocked

    class _Req:
        def __init__(self) -> None:
            self.app = type("App", (), {"state": _AppState()})()

    return _Req()


@pytest.fixture
def supabase_config(tmp_path) -> AppConfig:  # type: ignore[no-untyped-def]
    return AppConfig(
        debug=True,
        cors_origins=["https://iris-uat.test"],
        database=DatabaseConfig(data_dir=str(tmp_path / "data")),
        auth=AuthConfig(
            jwt_secret="iris-jwt-secret-32-bytes-long-for-hs256-ok",
            argon2_time_cost=1,
            argon2_memory_cost=8192,
            argon2_parallelism=1,
        ),
        supabase=SupabaseConfig(
            url="https://supabase.example.com",
            anon_key="anon",
            service_role_key="srv",
            db_url="postgres://example",
            jwt_secret="SUPABASE-DIFFERENT-secret-also-32-bytes-or-more",
        ),
        rate_limit_general=1000,
        rate_limit_pat=1000,
    )


@pytest.mark.asyncio
class TestHybridIrisOAuthInSupabaseMode:
    """Iris-OAuth tokens (aud='iris-mcp', signed with IRIS_JWT_SECRET)
    must validate in Supabase mode via the iris JWT decoder."""

    async def test_iris_oauth_token_validates_via_iris_secret(
        self, supabase_config: AppConfig,
    ) -> None:
        token = _make_iris_oauth_token(
            supabase_config.auth.jwt_secret, user_id="user-iris-oauth",
        )
        req = _fake_request(supabase_config)

        # Mock get_profile to return a populated profile.
        profile = {
            "id": "user-iris-oauth",
            "username": "iris-user",
            "role": "viewer",
            "is_active": True,
        }
        with patch(
            "app.auth.supabase_service.get_profile",
            new=AsyncMock(return_value=profile),
        ):
            result = await _get_current_user_supabase(req, token)

        assert result["id"] == "user-iris-oauth"
        assert result["username"] == "iris-user"
        assert result["role"] == "viewer"
        assert result["jti"] == "test-jti-12345"

    async def test_iris_oauth_token_with_wrong_signature_401(
        self, supabase_config: AppConfig,
    ) -> None:
        """A token claiming aud='iris-mcp' but signed with the WRONG
        secret must be rejected — the hybrid path doesn't fall through
        to the Supabase decoder for aud='iris-mcp' tokens (would let
        any Supabase-signed token forge an iris-OAuth identity)."""
        # Sign with a totally unrelated secret.
        bad_token = _make_iris_oauth_token(
            "wrong-secret-32-bytes-long-not-iris-jwt-secret",
            user_id="forged-user",
        )
        req = _fake_request(supabase_config)
        with pytest.raises(HTTPException) as exc:
            await _get_current_user_supabase(req, bad_token)
        assert exc.value.status_code == 401

    async def test_supabase_token_still_validates_via_supabase_path(
        self, supabase_config: AppConfig,
    ) -> None:
        """Tokens without aud='iris-mcp' must go through the Supabase
        decoder, not the iris path. Round-trip a Supabase-shaped token
        signed with SUPABASE_JWT_SECRET and confirm it routes there."""
        token = _make_supabase_shaped_token(
            supabase_config.supabase.jwt_secret, user_id="user-supabase",
        )
        req = _fake_request(supabase_config)

        profile = {
            "id": "user-supabase",
            "username": "sb-user",
            "role": "editor",
            "is_active": True,
        }

        # Mock JWKS fetch (returns no keys → falls to HS256 path inside
        # decode_supabase_jwt with the Supabase secret).
        with (
            patch(
                "app.auth.supabase_service.fetch_jwks",
                new=AsyncMock(return_value={"keys": []}),
            ),
            patch(
                "app.auth.supabase_service.get_profile",
                new=AsyncMock(return_value=profile),
            ),
        ):
            result = await _get_current_user_supabase(req, token)

        assert result["id"] == "user-supabase"
        assert result["role"] == "editor"
