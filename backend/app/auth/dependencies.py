"""FastAPI dependencies for authentication and authorization per SPEC-005-A/B."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import Depends, HTTPException, Request
from jose import JWTError

from app.auth.service import decode_access_token

if TYPE_CHECKING:
    from app.config import AuthConfig


async def get_current_user(request: Request) -> dict[str, Any]:
    """Extract and validate the current user from JWT bearer token.

    SQLite mode: decodes Iris-issued JWT, checks users table.
    Supabase mode: decodes Supabase-issued JWT, checks profiles table.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header[len("Bearer "):]
    config = request.app.state.config

    if config.db_backend == "supabase":
        return await _get_current_user_supabase(request, token)
    return await _get_current_user_sqlite(request, token)


async def _get_current_user_sqlite(
    request: Request,
    token: str,
) -> dict[str, Any]:
    """Validate Iris JWT and check users table (SQLite mode)."""
    config = request.app.state.config.auth
    try:
        payload = decode_access_token(token, config)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")  # noqa: B904

    user_id = payload.get("sub")
    role = payload.get("role")
    if not user_id or not role:
        raise HTTPException(status_code=401, detail="Invalid token claims")

    db = request.app.state.db_manager.main_db
    cursor = await db.execute(
        "SELECT id, username, role, is_active FROM users WHERE id = ?",
        (user_id,),
    )
    row = await cursor.fetchone()
    if row is None or not row[3]:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return {
        "id": row[0],
        "username": row[1],
        "role": row[2],
        "jti": payload.get("jti"),
    }


async def _get_current_user_supabase(
    request: Request,
    token: str,
) -> dict[str, Any]:
    """Validate Supabase JWT and check profiles table (Supabase mode)."""
    from app.auth.supabase_service import decode_supabase_jwt, get_profile  # noqa: PLC0415

    config = request.app.state.config
    if config.supabase is None:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    try:
        payload = decode_supabase_jwt(token, config.supabase.jwt_secret)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")  # noqa: B904

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token claims")

    db = request.app.state.db_manager.main_db
    profile = await get_profile(db, str(user_id))
    if profile is None or not profile["is_active"]:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return {
        "id": profile["id"],
        "username": profile["username"],
        "role": profile["role"],
        "jti": payload.get("jti"),
    }


def require_permission(permission: str) -> Any:
    """Create a dependency that checks if the current user has a permission."""

    async def check_permission(
        request: Request,
        current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
    ) -> dict[str, Any]:
        db = request.app.state.db_manager.main_db
        cursor = await db.execute(
            "SELECT permission FROM role_permissions WHERE role_id = ?",
            (current_user["role"],),
        )
        permissions = {row[0] for row in await cursor.fetchall()}
        if permission not in permissions:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return check_permission
