"""OAuth 2.1 service layer (ADR-164, SPEC-164-A).

- Dynamic Client Registration (RFC 7591).
- Authorization code issuance + PKCE-validated exchange.
- JWT access tokens (HS256, reuses existing JWT_SECRET).
- DB-stored opaque refresh tokens with family-id rotation/theft detection
  (mirrors the v5.x refresh_tokens pattern from app/auth/service.py).
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from jose import jwt

from app.oauth.pkce import verify_s256

if TYPE_CHECKING:
    import aiosqlite

    from app.config import AuthConfig

ACCESS_TOKEN_TTL = timedelta(hours=1)
AUTHORIZATION_CODE_TTL = timedelta(minutes=10)
REFRESH_TOKEN_TTL = timedelta(days=14)


def _utcnow_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


# ── Dynamic Client Registration ────────────────────────────────────


async def register_client(
    db: aiosqlite.Connection,
    *,
    client_name: str,
    redirect_uris: list[str],
    grant_types: list[str],
    token_endpoint_auth_method: str,
) -> dict[str, Any]:
    """Register a new OAuth client (RFC 7591). Open registration —
    any caller. Returns the issued client_id (+ secret if confidential).

    Confidential clients (token_endpoint_auth_method='client_secret_basic')
    receive a secret stored as a token_hex hash. Public clients
    (token_endpoint_auth_method='none', the default for PKCE-only flows)
    don't get a secret.
    """
    import json

    client_id = "iris-mcp-" + secrets.token_urlsafe(16)
    secret = None
    secret_hash = None
    if token_endpoint_auth_method == "client_secret_basic":
        secret = secrets.token_urlsafe(32)
        # Argon2 would be overkill; SHA256 is fine for opaque secrets
        # with no rainbow-table risk (32-byte urlsafe = 256-bit entropy).
        import hashlib
        secret_hash = hashlib.sha256(secret.encode("ascii")).hexdigest()

    await db.execute(
        "INSERT INTO oauth_clients ("
        "  client_id, client_secret_hash, client_name, redirect_uris,"
        "  grant_types, token_endpoint_auth_method, created_at"
        ") VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            client_id,
            secret_hash,
            client_name,
            json.dumps(redirect_uris),
            json.dumps(grant_types),
            token_endpoint_auth_method,
            _utcnow_iso(),
        ),
    )
    await db.commit()
    return {
        "client_id": client_id,
        "client_secret": secret,
        "client_name": client_name,
        "redirect_uris": redirect_uris,
        "grant_types": grant_types,
        "token_endpoint_auth_method": token_endpoint_auth_method,
        "client_id_issued_at": int(datetime.now(tz=UTC).timestamp()),
    }


async def get_client(
    db: aiosqlite.Connection, client_id: str,
) -> dict[str, Any] | None:
    """Look up a registered client. Returns row data or None."""
    import json

    cursor = await db.execute(
        "SELECT client_id, client_secret_hash, client_name, redirect_uris,"
        " grant_types, token_endpoint_auth_method"
        " FROM oauth_clients WHERE client_id = ?",
        (client_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return {
        "client_id": row[0],
        "client_secret_hash": row[1],
        "client_name": row[2],
        "redirect_uris": json.loads(row[3]),
        "grant_types": json.loads(row[4]),
        "token_endpoint_auth_method": row[5],
    }


# ── Authorization codes ────────────────────────────────────────────


async def create_authorization_code(
    db: aiosqlite.Connection,
    *,
    client_id: str,
    user_id: str,
    redirect_uri: str,
    code_challenge: str,
    code_challenge_method: str = "S256",
    scope: str = "iris",
) -> str:
    """Mint a fresh single-use authorization code (10-min TTL)."""
    code = secrets.token_urlsafe(32)
    expires_at = (datetime.now(tz=UTC) + AUTHORIZATION_CODE_TTL).isoformat()
    await db.execute(
        "INSERT INTO oauth_authorization_codes ("
        "  code, client_id, user_id, redirect_uri,"
        "  code_challenge, code_challenge_method, scope, expires_at"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            code, client_id, user_id, redirect_uri,
            code_challenge, code_challenge_method, scope, expires_at,
        ),
    )
    await db.commit()
    return code


async def consume_authorization_code(
    db: aiosqlite.Connection,
    *,
    code: str,
    client_id: str,
    redirect_uri: str,
    code_verifier: str,
) -> dict[str, Any] | None:
    """Validate + single-use-consume an authorization code.

    Returns the {user_id, scope} payload on success, None on any
    rejection cause (unknown / expired / already-used / client_id
    mismatch / redirect_uri mismatch / PKCE mismatch).
    """
    now_iso = _utcnow_iso()
    cursor = await db.execute(
        "SELECT client_id, user_id, redirect_uri, code_challenge,"
        " code_challenge_method, scope, expires_at, used_at"
        " FROM oauth_authorization_codes WHERE code = ?",
        (code,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    (
        row_client, user_id, row_redirect, code_challenge,
        challenge_method, scope, expires_at, used_at,
    ) = row

    if used_at is not None:
        return None
    if expires_at <= now_iso:
        return None
    if row_client != client_id:
        return None
    if row_redirect != redirect_uri:
        return None
    if challenge_method != "S256":
        return None
    if not verify_s256(code_verifier, code_challenge):
        return None

    # Mark used (single-use enforcement).
    await db.execute(
        "UPDATE oauth_authorization_codes SET used_at = ? WHERE code = ?",
        (now_iso, code),
    )
    await db.commit()
    return {"user_id": user_id, "scope": scope}


# ── Tokens ─────────────────────────────────────────────────────────


async def issue_access_token(
    db: aiosqlite.Connection,
    *,
    user_id: str,
    client_id: str,
    scope: str,
    config: AuthConfig,
) -> str:
    """Mint an OAuth access token (JWT, HS256, existing JWT_SECRET).

    Claims:
      sub  = user_id
      role = user's role (looked up from users table; required by
             `get_current_user` for early-rejection — same shape as
             /api/auth/login JWTs)
      aud  = "iris-mcp" (OAuth 2.1 audience)
      azp  = client_id (authorized party)
      scope = "iris" (or whatever grant scope)
      iat / exp / jti
    """
    cursor = await db.execute(
        "SELECT role FROM users WHERE id = ?",
        (user_id,),
    )
    row = await cursor.fetchone()
    role = row[0] if row else "viewer"

    now = datetime.now(tz=UTC)
    payload = {
        "sub": user_id,
        "role": role,
        "aud": "iris-mcp",
        "azp": client_id,
        "scope": scope,
        "iat": now,
        "exp": now + ACCESS_TOKEN_TTL,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)


async def create_refresh_token(
    db: aiosqlite.Connection,
    *,
    client_id: str,
    user_id: str,
    family_id: str | None = None,
) -> tuple[str, str]:
    """Mint a refresh token. Returns (token_value, family_id).

    family_id ties rotation chains together for theft detection: when a
    token from this family is presented after being marked `used`, the
    whole family is revoked (per v5.x refresh_tokens pattern, m001).
    """
    token_value = secrets.token_urlsafe(32)
    family = family_id or str(uuid.uuid4())
    now_iso = _utcnow_iso()
    expires_at = (datetime.now(tz=UTC) + REFRESH_TOKEN_TTL).isoformat()
    await db.execute(
        "INSERT INTO oauth_refresh_tokens ("
        "  id, client_id, user_id, family_id,"
        "  expires_at, created_at, revoked"
        ") VALUES (?, ?, ?, ?, ?, ?, 0)",
        (token_value, client_id, user_id, family, expires_at, now_iso),
    )
    await db.commit()
    return token_value, family


async def rotate_refresh_token(
    db: aiosqlite.Connection,
    *,
    presented_token: str,
    client_id: str,
) -> dict[str, Any] | None:
    """Validate + rotate a refresh token.

    On success: mark the presented token used, mint a fresh refresh
    token in the same family, return {user_id, scope, refresh_token}.

    On theft detection (used + presented again): revoke the whole
    family and return None.

    Returns None on any rejection cause.
    """
    now_iso = _utcnow_iso()
    cursor = await db.execute(
        "SELECT client_id, user_id, family_id, expires_at, used_at, revoked"
        " FROM oauth_refresh_tokens WHERE id = ?",
        (presented_token,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    row_client, user_id, family_id, expires_at, used_at, revoked = row

    if row_client != client_id:
        return None
    if expires_at <= now_iso:
        return None

    # Theft check runs BEFORE the explicit-revoked check so that a
    # replay of a (previously rotated) token triggers family kill-
    # switch. Rotation marks used_at but NOT revoked (`revoked` is
    # reserved for explicit revocation via /oauth/revoke or family
    # cascade) so this branch fires on every replay.
    if used_at is not None:
        await db.execute(
            "UPDATE oauth_refresh_tokens SET revoked = 1"
            " WHERE family_id = ?",
            (family_id,),
        )
        await db.commit()
        return None

    if revoked:
        return None

    # Mark used + mint a new refresh in the same family. Don't set
    # revoked — see comment above.
    await db.execute(
        "UPDATE oauth_refresh_tokens SET used_at = ?"
        " WHERE id = ?",
        (now_iso, presented_token),
    )
    new_token, _ = await create_refresh_token(
        db, client_id=client_id, user_id=user_id, family_id=family_id,
    )
    return {
        "user_id": user_id,
        "refresh_token": new_token,
        "scope": "iris",
    }


async def revoke_refresh_token(
    db: aiosqlite.Connection,
    *,
    token: str,
    client_id: str,
) -> bool:
    """Mark a refresh token revoked. Returns True if the row belonged
    to the client and was updated (idempotent on already-revoked tokens).
    RFC 7009 says revoke is always 200 OK regardless of success — the
    caller maps to that."""
    cursor = await db.execute(
        "UPDATE oauth_refresh_tokens SET revoked = 1"
        " WHERE id = ? AND client_id = ?",
        (token, client_id),
    )
    await db.commit()
    return cursor.rowcount > 0


# ── Consent payload cache (in-memory, per-process) ─────────────────


_CONSENT_CACHE: dict[str, dict[str, Any]] = {}


def cache_consent_payload(payload: dict[str, Any]) -> str:
    """Stash an in-progress authorize request keyed by a fresh
    request_id. Returns the request_id.

    The cache is per-process and short-lived (10-min TTL — same as
    the auth code TTL). Multi-process iris-backend deployments would
    promote this to Redis; single-instance Render deploys can use
    in-memory."""
    request_id = secrets.token_urlsafe(24)
    _CONSENT_CACHE[request_id] = {
        **payload,
        "expires_at": (datetime.now(tz=UTC) + AUTHORIZATION_CODE_TTL).isoformat(),
    }
    return request_id


def pop_consent_payload(request_id: str) -> dict[str, Any] | None:
    """Retrieve + remove a cached consent payload. Returns None if
    unknown or expired."""
    payload = _CONSENT_CACHE.pop(request_id, None)
    if payload is None:
        return None
    if payload.get("expires_at", "") <= _utcnow_iso():
        return None
    return payload
