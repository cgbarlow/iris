"""Tests for authentication service."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from argon2 import PasswordHasher
from jose import jwt

from app.auth.service import (
    check_password_history,
    create_access_token,
    create_password_hasher,
    create_refresh_token,
    decode_access_token,
    revoke_user_tokens,
    rotate_refresh_token,
    validate_password,
)
from app.config import AuthConfig
from app.migrations.m001_roles_users import up as m001_up
from app.migrations.seed import seed_roles_and_permissions

if TYPE_CHECKING:
    import aiosqlite


@pytest.fixture
def auth_config() -> AuthConfig:
    return AuthConfig(
        jwt_secret="test-secret-key-that-is-at-least-32-bytes-long-for-hs256",
        argon2_time_cost=1,
        argon2_memory_cost=8192,
        argon2_parallelism=1,
    )


@pytest.fixture
def hasher(auth_config: AuthConfig) -> PasswordHasher:
    return create_password_hasher(auth_config)


class TestPasswordHashing:
    """Verify Argon2id password hashing."""

    def test_creates_argon2id_hasher(self, auth_config: AuthConfig) -> None:
        ph = create_password_hasher(auth_config)
        assert isinstance(ph, PasswordHasher)

    def test_hash_and_verify(self, hasher: PasswordHasher) -> None:
        hashed = hasher.hash("MySecureP@ss123")
        assert hasher.verify(hashed, "MySecureP@ss123")

    def test_hash_contains_argon2id(self, hasher: PasswordHasher) -> None:
        hashed = hasher.hash("TestPassword1!")
        assert "$argon2id$" in hashed


class TestPasswordValidation:
    """Verify password validation rules per SPEC-005-B."""

    def test_valid_password(self, auth_config: AuthConfig) -> None:
        errors = validate_password("MySecureP@ss1", auth_config)
        assert errors == []

    def test_too_short(self, auth_config: AuthConfig) -> None:
        errors = validate_password("Short1!", auth_config)
        assert any("at least 12" in e for e in errors)

    def test_too_long(self, auth_config: AuthConfig) -> None:
        errors = validate_password("A" * 129 + "1!", auth_config)
        assert any("at most 128" in e for e in errors)

    def test_insufficient_complexity(self, auth_config: AuthConfig) -> None:
        errors = validate_password("alllowercase!", auth_config)
        assert any("3 of" in e for e in errors)

    def test_common_password(self, auth_config: AuthConfig) -> None:
        errors = validate_password("password1234", auth_config)
        assert any("too common" in e for e in errors)

    def test_three_classes_valid(self, auth_config: AuthConfig) -> None:
        # lowercase + uppercase + digit = 3 classes
        errors = validate_password("MyPassword12", auth_config)
        assert errors == []


class TestJWTCreation:
    """Verify JWT access token creation and decoding."""

    def test_create_access_token(self, auth_config: AuthConfig) -> None:
        token, jti = create_access_token("user1", "admin", auth_config)
        assert isinstance(token, str)
        assert len(token) > 0
        assert len(jti) > 0

    def test_decode_access_token(self, auth_config: AuthConfig) -> None:
        token, jti = create_access_token("user1", "admin", auth_config)
        payload = decode_access_token(token, auth_config)
        assert payload["sub"] == "user1"
        assert payload["role"] == "admin"
        assert payload["jti"] == jti

    def test_token_has_expiry(self, auth_config: AuthConfig) -> None:
        token, _ = create_access_token("user1", "admin", auth_config)
        payload = decode_access_token(token, auth_config)
        assert "exp" in payload

    def test_token_uses_hs256(self, auth_config: AuthConfig) -> None:
        token, _ = create_access_token("user1", "admin", auth_config)
        header = jwt.get_unverified_header(token)
        assert header["alg"] == "HS256"


class TestRefreshTokens:
    """Verify refresh token creation, rotation, and revocation."""

    async def _setup(self, db: aiosqlite.Connection) -> None:
        await m001_up(db)
        await seed_roles_and_permissions(db)
        await db.execute(
            "INSERT INTO users (id, username, password_hash, role) "
            "VALUES ('user1', 'admin', 'hash', 'admin')"
        )
        await db.commit()

    async def test_create_refresh_token(
        self, main_db: aiosqlite.Connection, auth_config: AuthConfig
    ) -> None:
        await self._setup(main_db)
        token = await create_refresh_token(main_db, "user1", auth_config)
        assert isinstance(token, str)
        assert len(token) > 0

    async def test_rotate_refresh_token(
        self, main_db: aiosqlite.Connection, auth_config: AuthConfig
    ) -> None:
        await self._setup(main_db)
        token = await create_refresh_token(main_db, "user1", auth_config)
        result = await rotate_refresh_token(main_db, token, auth_config)
        assert result is not None
        new_token, user_id = result
        assert user_id == "user1"
        assert new_token != token

    async def test_reuse_detection_revokes_family(
        self, main_db: aiosqlite.Connection, auth_config: AuthConfig
    ) -> None:
        await self._setup(main_db)
        token = await create_refresh_token(main_db, "user1", auth_config)

        # First rotation succeeds
        result = await rotate_refresh_token(main_db, token, auth_config)
        assert result is not None

        # Reuse of old token triggers family revocation
        result = await rotate_refresh_token(main_db, token, auth_config)
        assert result is None

    async def test_revoke_user_tokens(
        self, main_db: aiosqlite.Connection, auth_config: AuthConfig
    ) -> None:
        await self._setup(main_db)
        token = await create_refresh_token(main_db, "user1", auth_config)
        await revoke_user_tokens(main_db, "user1")
        result = await rotate_refresh_token(main_db, token, auth_config)
        assert result is None

    async def test_nonexistent_token_returns_none(
        self, main_db: aiosqlite.Connection, auth_config: AuthConfig
    ) -> None:
        await self._setup(main_db)
        result = await rotate_refresh_token(
            main_db, "nonexistent", auth_config
        )
        assert result is None


class TestPasswordHistory:
    """Verify password history checking."""

    async def _setup(self, db: aiosqlite.Connection) -> None:
        await m001_up(db)
        await seed_roles_and_permissions(db)
        await db.execute(
            "INSERT INTO users (id, username, password_hash, role) "
            "VALUES ('user1', 'admin', 'hash', 'admin')"
        )
        await db.commit()

    async def test_no_history_returns_false(
        self,
        main_db: aiosqlite.Connection,
        hasher: PasswordHasher,
    ) -> None:
        await self._setup(main_db)
        result = await check_password_history(
            main_db, "user1", "NewPassword1!", hasher, 5
        )
        assert result is False

    async def test_detects_password_in_history(
        self,
        main_db: aiosqlite.Connection,
        hasher: PasswordHasher,
    ) -> None:
        await self._setup(main_db)
        old_hash = hasher.hash("OldPassword1!")
        await main_db.execute(
            "INSERT INTO password_history (user_id, password_hash) "
            "VALUES ('user1', ?)",
            (old_hash,),
        )
        await main_db.commit()
        result = await check_password_history(
            main_db, "user1", "OldPassword1!", hasher, 5
        )
        assert result is True

    async def test_different_password_returns_false(
        self,
        main_db: aiosqlite.Connection,
        hasher: PasswordHasher,
    ) -> None:
        await self._setup(main_db)
        old_hash = hasher.hash("OldPassword1!")
        await main_db.execute(
            "INSERT INTO password_history (user_id, password_hash) "
            "VALUES ('user1', ?)",
            (old_hash,),
        )
        await main_db.commit()
        result = await check_password_history(
            main_db, "user1", "CompletelyNew1!", hasher, 5
        )
        assert result is False
