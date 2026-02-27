"""Pydantic models for user management."""

from __future__ import annotations

from pydantic import BaseModel, Field


class UserCreateRequest(BaseModel):
    """Request body for creating a user (admin only)."""

    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=12, max_length=128)
    role: str = Field(default="viewer")


class UserUpdateRequest(BaseModel):
    """Request body for updating a user (admin only)."""

    role: str | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    """Response for a single user."""

    id: str
    username: str
    role: str
    is_active: bool
    created_at: str
    last_login_at: str | None = None
