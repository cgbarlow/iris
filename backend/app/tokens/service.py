"""Personal Access Token service (ADR-127, SPEC-127-A).

- `generate_token` — mints a new `iris_pat_<prefix>_<secret>` and stores
  the Argon2id hash of the secret. Returns (full_token, prefix, hash).
- `verify_pat` — validates a bearer value, looks up by prefix, verifies
  the hash, rejects revoked/expired, touches last_used_at, and returns
  the authenticated user dict in the shape `get_current_user` uses.
- `list_tokens` / `create_token` / `revoke_token` — management helpers
  used by the router.

The hash uses the same Argon2id parameters as password hashing so the
Argon2id keying material is consistent across the deployment (NZISM).
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

if TYPE_CHECKING:
    import aiosqlite

    from app.config import AuthConfig


PAT_PREFIX = "iris_pat_"
PREFIX_HEX_BYTES = 4  # → 8 hex chars, no `_` or `-`, safe to use as a lookup key
SECRET_BYTES = 32     # urlsafe encoding -> ~43 chars


def create_pat_hasher(config: AuthConfig) -> PasswordHasher:
    """Return an Argon2id hasher configured for PAT secret hashing.

    Same parameters as the password hasher — NZISM wants a single
    consistent Argon2id posture across credentials.
    """
    return PasswordHasher(
        time_cost=config.argon2_time_cost,
        memory_cost=config.argon2_memory_cost,
        parallelism=config.argon2_parallelism,
        hash_len=32,
    )


def generate_token(hasher: PasswordHasher) -> tuple[str, str, str]:
    """Mint a new PAT. Returns (full_token, prefix, token_hash).

    Prefix uses hex digits only (no ``_`` / ``-``) so the ``iris_pat_``
    prefix can be split off the token with a simple single-underscore
    separator, and the remaining portion is unambiguously the secret.
    """
    prefix = secrets.token_hex(PREFIX_HEX_BYTES)  # 8 hex chars
    secret = secrets.token_urlsafe(SECRET_BYTES)
    full = f"{PAT_PREFIX}{prefix}_{secret}"
    token_hash = hasher.hash(secret)
    return full, prefix, token_hash


def _parse(token: str) -> tuple[str, str] | None:
    """Split `iris_pat_<prefix>_<secret>` into (prefix, secret).

    Returns None on malformed input rather than raising — the caller
    maps that to a 401.
    """
    if not token.startswith(PAT_PREFIX):
        return None
    tail = token[len(PAT_PREFIX):]
    parts = tail.split("_", 1)
    if len(parts) != 2:  # noqa: PLR2004 — prefix + secret, always exactly two parts
        return None
    prefix, secret = parts
    if len(prefix) != PREFIX_HEX_BYTES * 2 or not secret:
        return None
    return prefix, secret


async def verify_pat(  # noqa: PLR0911 — short-circuit returns for distinct rejection cases
    db: aiosqlite.Connection,
    token: str,
    hasher: PasswordHasher,
) -> dict[str, Any] | None:
    """Verify a PAT bearer value. Returns the user dict or None.

    Rejects (→ None) on: malformed token, unknown prefix, hash mismatch,
    revoked, expired, or inactive user. Successful calls touch
    `last_used_at` on the PAT row.
    """
    parsed = _parse(token)
    if parsed is None:
        return None
    prefix, secret = parsed

    now = datetime.now(tz=UTC).isoformat()

    cursor = await db.execute(
        "SELECT pat.id, pat.user_id, pat.token_hash, pat.revoked_at, pat.expires_at,"
        " u.username, u.role, u.is_active"
        " FROM personal_access_tokens pat"
        " JOIN users u ON u.id = pat.user_id"
        " WHERE pat.prefix = ?",
        (prefix,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    pat_id, user_id, token_hash, revoked_at, expires_at, username, role, is_active = row

    if revoked_at is not None:
        return None
    if expires_at is not None and expires_at <= now:
        return None
    if not is_active:
        return None

    try:
        hasher.verify(token_hash, secret)
    except VerifyMismatchError:
        return None

    await db.execute(
        "UPDATE personal_access_tokens SET last_used_at = ? WHERE id = ?",
        (now, pat_id),
    )
    await db.commit()

    return {
        "id": user_id,
        "username": username,
        "role": role,
        "jti": pat_id,  # the PAT id doubles as the token's jti for audit parity
        "auth_type": "pat",
    }


async def list_tokens(
    db: aiosqlite.Connection,
    user_id: str,
) -> list[dict[str, Any]]:
    """Return all PATs for the given user, most recent first. No secrets."""
    cursor = await db.execute(
        "SELECT id, name, prefix, created_at, last_used_at, expires_at, revoked_at"
        " FROM personal_access_tokens"
        " WHERE user_id = ?"
        " ORDER BY created_at DESC",
        (user_id,),
    )
    rows = await cursor.fetchall()
    return [
        {
            "id": r[0],
            "name": r[1],
            "prefix": r[2],
            "created_at": r[3],
            "last_used_at": r[4],
            "expires_at": r[5],
            "revoked_at": r[6],
        }
        for r in rows
    ]


async def create_token(
    db: aiosqlite.Connection,
    user_id: str,
    name: str,
    expires_at: datetime | None,
    hasher: PasswordHasher,
) -> dict[str, Any]:
    """Create a PAT and return the record including the plaintext token."""
    full_token, prefix, token_hash = generate_token(hasher)
    pat_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    expires_iso = expires_at.astimezone(UTC).isoformat() if expires_at else None

    await db.execute(
        "INSERT INTO personal_access_tokens"
        " (id, user_id, name, token_hash, prefix, created_at, expires_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (pat_id, user_id, name, token_hash, prefix, now, expires_iso),
    )
    await db.commit()

    return {
        "id": pat_id,
        "name": name,
        "prefix": prefix,
        "created_at": now,
        "last_used_at": None,
        "expires_at": expires_iso,
        "revoked_at": None,
        "token": full_token,
    }


async def revoke_token(
    db: aiosqlite.Connection,
    user_id: str,
    token_id: str,
) -> bool:
    """Soft-revoke a PAT. Returns True if the row belonged to the user
    and was updated (idempotent on already-revoked tokens); False if the
    row does not exist or belongs to another user.
    """
    now = datetime.now(tz=UTC).isoformat()
    cursor = await db.execute(
        "UPDATE personal_access_tokens SET revoked_at = COALESCE(revoked_at, ?)"
        " WHERE id = ? AND user_id = ?",
        (now, token_id, user_id),
    )
    await db.commit()
    return cursor.rowcount > 0
