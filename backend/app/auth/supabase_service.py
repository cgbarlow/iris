"""Supabase JWT validation and profiles table lookup for Supabase deployment mode."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from jose import jwt

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


def decode_supabase_jwt(token: str, jwt_secret: str) -> dict[str, Any]:
    """Decode and validate a Supabase-issued JWT.

    Supabase signs JWTs with HS256 using the project's JWT secret.
    The 'sub' claim contains the user's UUID.
    The 'role' claim is 'authenticated' (not the application role).
    Application roles are stored in the profiles table.
    """
    payload: dict[str, Any] = jwt.decode(
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
