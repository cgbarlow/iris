"""Tests for Supabase JWT validation (supabase_service.py)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt
from jose.exceptions import JWTError

from app.auth.supabase_service import decode_supabase_jwt

JWT_SECRET = "test-supabase-jwt-secret-at-least-32-bytes-long!"


def _make_token(claims: dict, secret: str = JWT_SECRET) -> str:
    return jwt.encode(claims, secret, algorithm="HS256")


def test_decode_valid_token() -> None:
    user_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC)
    token = _make_token({
        "sub": user_id,
        "role": "authenticated",
        "iat": now,
        "exp": now + timedelta(hours=1),
    })
    payload = decode_supabase_jwt(token, JWT_SECRET)
    assert payload["sub"] == user_id
    assert payload["role"] == "authenticated"


def test_decode_token_with_aud_claim() -> None:
    """Supabase tokens carry aud='authenticated'; we skip aud verification."""
    user_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC)
    token = _make_token({
        "sub": user_id,
        "aud": "authenticated",
        "role": "authenticated",
        "exp": now + timedelta(hours=1),
    })
    # Must not raise even though aud is present
    payload = decode_supabase_jwt(token, JWT_SECRET)
    assert payload["sub"] == user_id


def test_decode_expired_token_raises() -> None:
    token = _make_token({
        "sub": str(uuid.uuid4()),
        "exp": datetime.now(tz=UTC) - timedelta(seconds=1),
    })
    with pytest.raises(JWTError):
        decode_supabase_jwt(token, JWT_SECRET)


def test_decode_wrong_secret_raises() -> None:
    token = _make_token({
        "sub": str(uuid.uuid4()),
        "exp": datetime.now(tz=UTC) + timedelta(hours=1),
    })
    with pytest.raises(JWTError):
        decode_supabase_jwt(token, "wrong-secret-at-least-32-bytes-long!!!!!")


def test_decode_returns_all_claims() -> None:
    user_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC)
    email = "alice@example.com"
    token = _make_token({
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
        "exp": now + timedelta(hours=1),
    })
    payload = decode_supabase_jwt(token, JWT_SECRET)
    assert payload["email"] == email
    assert payload["sub"] == user_id
