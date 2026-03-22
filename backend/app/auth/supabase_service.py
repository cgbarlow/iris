"""Supabase JWT validation and profiles table lookup for Supabase deployment mode."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import httpx
from jose import jwt

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort

logger = logging.getLogger(__name__)

# Cache for JWKS keys fetched from Supabase
_jwks_cache: dict[str, Any] | None = None


async def fetch_jwks(supabase_url: str) -> dict[str, Any]:
    """Fetch JWKS from Supabase auth endpoint and cache it."""
    global _jwks_cache  # noqa: PLW0603
    if _jwks_cache is not None:
        return _jwks_cache
    jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(jwks_url, timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()
    logger.info("Fetched JWKS from %s", jwks_url)
    return _jwks_cache


def decode_supabase_jwt(
    token: str, jwt_secret: str, jwks: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Decode and validate a Supabase-issued JWT.

    Supports both legacy HS256 (shared secret) and new ES256 (JWKS/ECC P-256)
    signing methods. Tries ES256 via JWKS first if available, falls back to HS256.

    The 'sub' claim contains the user's UUID.
    The 'role' claim is 'authenticated' (not the application role).
    Application roles are stored in the profiles table.
    """
    # Try ES256 with JWKS first (new Supabase projects use ECC P-256)
    if jwks and jwks.get("keys"):
        # Extract the unverified header to find the matching key
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        for key in jwks["keys"]:
            if key.get("kid") == kid:
                payload: dict[str, Any] = jwt.decode(
                    token,
                    key,
                    algorithms=["ES256"],
                    options={"verify_aud": False},
                )
                return payload

    # Fall back to HS256 with shared secret (legacy Supabase projects)
    payload = jwt.decode(
        token,
        jwt_secret,
        algorithms=["HS256"],
        options={"verify_aud": False},
    )
    return payload


async def get_profile(
    db: DatabasePort,
    user_id: str,
) -> dict[str, Any] | None:
    """Look up a user profile by Supabase auth user ID.

    Returns None if the profile does not exist.
    Casts id to text for comparison since profiles.id is UUID type.
    """
    cursor = await db.execute(
        "SELECT id::text, username, role, is_active "
        "FROM profiles WHERE id::text = ?",
        (user_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return {
        "id": str(row[0]),
        "username": row[1],
        "role": row[2],
        "is_active": bool(row[3]),
    }
