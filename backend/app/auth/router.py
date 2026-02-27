"""Auth API routes per SPEC-005-B."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import get_current_user
from app.auth.models import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    SetupRequest,
    TokenResponse,
)
from app.auth.service import (
    check_password_history,
    create_access_token,
    create_password_hasher,
    create_refresh_token,
    revoke_user_tokens,
    rotate_refresh_token,
    validate_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request) -> TokenResponse:
    """Authenticate user and issue tokens per SPEC-005-B login flow."""
    config = request.app.state.config
    db = request.app.state.db_manager.main_db
    hasher = create_password_hasher(config.auth)

    # 1. Look up user
    cursor = await db.execute(
        "SELECT id, username, password_hash, role, is_active, "
        "failed_login_count, locked_until FROM users WHERE username = ?",
        (body.username,),
    )
    row = await cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id, _, password_hash, role, is_active = (
        row[0], row[1], row[2], row[3], row[4]
    )
    failed_count, locked_until = row[5], row[6]

    if not is_active:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 2. Check lockout
    if locked_until:
        lock_time = datetime.fromisoformat(locked_until)
        if lock_time > datetime.now(tz=UTC):
            raise HTTPException(status_code=401, detail="Account locked")

    # 3. Verify password
    try:
        hasher.verify(password_hash, body.password)
    except VerifyMismatchError:
        # Increment failed count
        new_count = failed_count + 1
        lock_until_val = None
        if new_count >= config.auth.max_failed_logins:
            lock_until_val = (
                datetime.now(tz=UTC)
                + timedelta(minutes=config.auth.lockout_minutes)
            ).isoformat()

        await db.execute(
            "UPDATE users SET failed_login_count = ?, locked_until = ? "
            "WHERE id = ?",
            (new_count, lock_until_val, user_id),
        )
        await db.commit()
        raise HTTPException(  # noqa: B904
            status_code=401, detail="Invalid credentials"
        )

    # 4. Success — reset failed count, generate tokens
    await db.execute(
        "UPDATE users SET failed_login_count = 0, locked_until = NULL, "
        "last_login_at = ? WHERE id = ?",
        (datetime.now(tz=UTC).isoformat(), user_id),
    )
    await db.commit()

    access_token, _jti = create_access_token(user_id, role, config.auth)
    refresh_token = await create_refresh_token(db, user_id, config.auth)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=config.auth.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, request: Request) -> TokenResponse:
    """Rotate refresh token and issue new access token."""
    config = request.app.state.config
    db = request.app.state.db_manager.main_db

    result = await rotate_refresh_token(db, body.refresh_token, config.auth)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    new_refresh_token, user_id = result

    # Get user role
    cursor = await db.execute(
        "SELECT role FROM users WHERE id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="User not found")

    access_token, _ = create_access_token(user_id, row[0], config.auth)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=config.auth.access_token_expire_minutes * 60,
    )


@router.post("/logout")
async def logout(
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, str]:
    """Revoke all refresh tokens for the current user."""
    db = request.app.state.db_manager.main_db
    await revoke_user_tokens(db, current_user["id"])
    return {"message": "Logged out"}


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, str]:
    """Change password per SPEC-005-B change-password flow."""
    config = request.app.state.config
    db = request.app.state.db_manager.main_db
    hasher = create_password_hasher(config.auth)

    # 1. Verify current password
    cursor = await db.execute(
        "SELECT password_hash FROM users WHERE id = ?",
        (current_user["id"],),
    )
    row = await cursor.fetchone()

    try:
        hasher.verify(row[0], body.current_password)
    except VerifyMismatchError:
        raise HTTPException(  # noqa: B904
            status_code=400, detail="Current password is incorrect"
        )

    # 2. Validate new password
    errors = validate_password(body.new_password, config.auth)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    # 3. Check password history
    in_history = await check_password_history(
        db, current_user["id"], body.new_password, hasher,
        config.auth.password_history_count,
    )
    if in_history:
        raise HTTPException(
            status_code=400, detail="Password was recently used"
        )

    # 4. Store old hash in history, update password
    await db.execute(
        "INSERT INTO password_history (user_id, password_hash) "
        "VALUES (?, ?)",
        (current_user["id"], row[0]),
    )
    new_hash = hasher.hash(body.new_password)
    await db.execute(
        "UPDATE users SET password_hash = ?, password_changed_at = ?, "
        "updated_at = ? WHERE id = ?",
        (
            new_hash,
            datetime.now(tz=UTC).isoformat(),
            datetime.now(tz=UTC).isoformat(),
            current_user["id"],
        ),
    )
    await db.commit()

    # 5. Revoke all refresh tokens
    await revoke_user_tokens(db, current_user["id"])

    return {"message": "Password changed"}


@router.get("/setup/status")
async def setup_status(request: Request) -> dict[str, bool]:
    """Check whether first-run setup is needed."""
    db = request.app.state.db_manager.main_db
    cursor = await db.execute("SELECT COUNT(*) FROM users")
    row = await cursor.fetchone()
    return {"needs_setup": row[0] == 0}


@router.post("/setup")
async def setup(body: SetupRequest, request: Request) -> dict[str, str]:
    """First-run admin setup — creates initial admin user."""
    config = request.app.state.config
    db = request.app.state.db_manager.main_db

    # Check if any users exist
    cursor = await db.execute("SELECT COUNT(*) FROM users")
    row = await cursor.fetchone()
    if row[0] > 0:
        raise HTTPException(
            status_code=400, detail="Setup already completed"
        )

    # Validate password
    errors = validate_password(body.password, config.auth)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    # Create admin user
    hasher = create_password_hasher(config.auth)
    user_id = str(uuid.uuid4())
    password_hash = hasher.hash(body.password)

    await db.execute(
        "INSERT INTO users (id, username, password_hash, role) "
        "VALUES (?, ?, ?, 'admin')",
        (user_id, body.username, password_hash),
    )
    await db.commit()

    return {"message": "Admin user created", "user_id": user_id}
