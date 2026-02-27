"""Pydantic models for authentication requests and responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login request body."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Access + refresh token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int


class RefreshRequest(BaseModel):
    """Token refresh request body."""

    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Change password request body."""

    current_password: str
    new_password: str = Field(min_length=12, max_length=128)


class SetupRequest(BaseModel):
    """First-run admin setup request body."""

    username: str
    password: str = Field(min_length=12, max_length=128)


class UserResponse(BaseModel):
    """User information response (no password hash)."""

    id: str
    username: str
    role: str
    is_active: bool
    last_login_at: str | None = None
    created_at: str
