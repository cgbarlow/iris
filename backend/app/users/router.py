"""User management API routes per SPEC-005-A/B."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import get_current_user
from app.auth.service import create_password_hasher, validate_password
from app.users.models import UserCreateRequest, UserResponse, UserUpdateRequest

router = APIRouter(prefix="/api/users", tags=["users"])


def _require_admin(current_user: dict[str, Any]) -> None:
    """Raise 403 if not admin."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("", response_model=list[UserResponse])
async def list_users(
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[UserResponse]:
    """List all users (admin only)."""
    _require_admin(current_user)
    db = request.app.state.db_manager.main_db
    cursor = await db.execute(
        "SELECT id, username, role, is_active, created_at, last_login_at "
        "FROM users ORDER BY created_at"
    )
    rows = await cursor.fetchall()
    return [
        UserResponse(
            id=r[0], username=r[1], role=r[2],
            is_active=bool(r[3]), created_at=r[4], last_login_at=r[5],
        )
        for r in rows
    ]


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    body: UserCreateRequest,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> UserResponse:
    """Create a new user (admin only)."""
    _require_admin(current_user)
    config = request.app.state.config
    db = request.app.state.db_manager.main_db

    # Validate password
    errors = validate_password(body.password, config.auth)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    # Check username uniqueness
    cursor = await db.execute(
        "SELECT id FROM users WHERE username = ?", (body.username,),
    )
    if await cursor.fetchone():
        raise HTTPException(status_code=409, detail="Username already exists")

    hasher = create_password_hasher(config.auth)
    user_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    password_hash = hasher.hash(body.password)

    await db.execute(
        "INSERT INTO users (id, username, password_hash, role, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, body.username, password_hash, body.role, now),
    )
    await db.commit()

    return UserResponse(
        id=user_id, username=body.username, role=body.role,
        is_active=True, created_at=now,
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    body: UserUpdateRequest,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> UserResponse:
    """Update a user's role or active status (admin only)."""
    _require_admin(current_user)
    db = request.app.state.db_manager.main_db

    cursor = await db.execute(
        "SELECT id, username, role, is_active, created_at, last_login_at "
        "FROM users WHERE id = ?",
        (user_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")

    new_role = body.role if body.role is not None else row[2]
    new_active = body.is_active if body.is_active is not None else bool(row[3])

    await db.execute(
        "UPDATE users SET role = ?, is_active = ?, updated_at = ? WHERE id = ?",
        (new_role, new_active, datetime.now(tz=UTC).isoformat(), user_id),
    )
    await db.commit()

    return UserResponse(
        id=row[0], username=row[1], role=new_role,
        is_active=new_active, created_at=row[4], last_login_at=row[5],
    )
