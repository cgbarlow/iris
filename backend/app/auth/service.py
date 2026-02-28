"""Authentication service per SPEC-005-B.

Provides Argon2id password hashing, password validation, JWT creation,
refresh token management, and all authentication flows.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import jwt

if TYPE_CHECKING:
    import aiosqlite

    from app.config import AuthConfig

# Top 20 common passwords (subset of 10k list)
COMMON_PASSWORDS = frozenset({
    "password", "123456789012", "qwertyuiop12", "password1234",
    "iloveyou1234", "letmein12345", "welcome12345", "monkey123456",
    "dragon123456", "master123456", "qwerty123456", "login1234567",
    "princess1234", "football1234", "shadow123456", "sunshine1234",
    "trustno11234", "admin1234567", "welcome1234!", "passw0rd1234",
})


def create_password_hasher(config: AuthConfig) -> PasswordHasher:
    """Create an Argon2id password hasher with SPEC-005-B parameters."""
    return PasswordHasher(
        time_cost=config.argon2_time_cost,
        memory_cost=config.argon2_memory_cost,
        parallelism=config.argon2_parallelism,
        hash_len=32,
        salt_len=16,
    )


def validate_password(password: str, config: AuthConfig) -> list[str]:
    """Validate password against SPEC-005-B requirements. Returns list of errors."""
    errors: list[str] = []

    if len(password) < config.min_password_length:
        errors.append(
            f"Password must be at least {config.min_password_length} characters"
        )
    if len(password) > config.max_password_length:
        errors.append(
            f"Password must be at most {config.max_password_length} characters"
        )

    # Complexity: at least 3 of 4 character classes
    classes = 0
    if re.search(r"[a-z]", password):
        classes += 1
    if re.search(r"[A-Z]", password):
        classes += 1
    if re.search(r"[0-9]", password):
        classes += 1
    if re.search(r"[^a-zA-Z0-9]", password):
        classes += 1

    min_classes = 3
    if classes < min_classes:
        errors.append(
            "Password must contain at least 3 of: lowercase, uppercase, "
            "digits, special characters"
        )

    # Common password check
    if password.lower() in COMMON_PASSWORDS:
        errors.append("Password is too common")

    return errors


def create_access_token(
    user_id: str,
    role: str,
    config: AuthConfig,
    timeout_minutes: int | None = None,
) -> tuple[str, str]:
    """Create a JWT access token. Returns (token, jti).

    If timeout_minutes is provided, it overrides the config default.
    """
    jti = str(uuid.uuid4())
    now = datetime.now(tz=UTC)
    expire_minutes = timeout_minutes or config.access_token_expire_minutes
    payload: dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "jti": jti,
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
    }
    token: str = jwt.encode(
        payload, config.jwt_secret, algorithm=config.jwt_algorithm
    )
    return token, jti


def decode_access_token(
    token: str, config: AuthConfig
) -> dict[str, Any]:
    """Decode and validate a JWT access token."""
    payload: dict[str, Any] = jwt.decode(
        token, config.jwt_secret, algorithms=[config.jwt_algorithm]
    )
    return payload


async def create_refresh_token(
    db: aiosqlite.Connection,
    user_id: str,
    config: AuthConfig,
    family_id: str | None = None,
) -> str:
    """Create a refresh token stored in the database. Returns the token value."""
    token_id = str(uuid.uuid4())
    if family_id is None:
        family_id = token_id
    expires_at = (
        datetime.now(tz=UTC) + timedelta(days=config.refresh_token_expire_days)
    ).isoformat()

    await db.execute(
        "INSERT INTO refresh_tokens (id, user_id, family_id, expires_at) "
        "VALUES (?, ?, ?, ?)",
        (token_id, user_id, family_id, expires_at),
    )
    await db.commit()
    return token_id


async def rotate_refresh_token(
    db: aiosqlite.Connection,
    old_token_id: str,
    config: AuthConfig,
) -> tuple[str, str] | None:
    """Rotate a refresh token. Returns (new_token, user_id) or None if invalid.

    Implements token family tracking for theft detection per SPEC-005-B.
    """
    cursor = await db.execute(
        "SELECT id, user_id, family_id, expires_at, used_at, revoked "
        "FROM refresh_tokens WHERE id = ?",
        (old_token_id,),
    )
    row = await cursor.fetchone()

    if row is None:
        return None

    token_id, user_id, family_id, expires_at, used_at, revoked = (
        row[0], row[1], row[2], row[3], row[4], row[5]
    )

    # Check if revoked
    if revoked:
        return None

    # Check if expired
    if datetime.fromisoformat(expires_at) < datetime.now(tz=UTC):
        return None

    # Check for token reuse (theft detection)
    if used_at is not None:
        # Revoke entire family
        await db.execute(
            "UPDATE refresh_tokens SET revoked = 1 WHERE family_id = ?",
            (family_id,),
        )
        await db.commit()
        return None

    # Mark current token as used
    await db.execute(
        "UPDATE refresh_tokens SET used_at = ? WHERE id = ?",
        (datetime.now(tz=UTC).isoformat(), token_id),
    )

    # Create new token in same family
    new_token = await create_refresh_token(
        db, user_id, config, family_id=family_id
    )
    return new_token, user_id


async def revoke_user_tokens(
    db: aiosqlite.Connection, user_id: str
) -> None:
    """Revoke all refresh tokens for a user."""
    await db.execute(
        "UPDATE refresh_tokens SET revoked = 1 WHERE user_id = ?",
        (user_id,),
    )
    await db.commit()


async def check_password_history(
    db: aiosqlite.Connection,
    user_id: str,
    new_password: str,
    hasher: PasswordHasher,
    history_count: int,
) -> bool:
    """Check if password was recently used. Returns True if password is in history."""
    cursor = await db.execute(
        "SELECT password_hash FROM password_history "
        "WHERE user_id = ? ORDER BY changed_at DESC LIMIT ?",
        (user_id, history_count),
    )
    rows = await cursor.fetchall()
    for row in rows:
        try:
            if hasher.verify(row[0], new_password):
                return True
        except VerifyMismatchError:
            continue
    return False
