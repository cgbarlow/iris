"""Pydantic models for the edit locking system (ADR-080)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LockAcquireRequest(BaseModel):
    """Request body for acquiring a lock."""

    target_type: str = Field(pattern=r"^(diagram|element|package)$")
    target_id: str = Field(min_length=1)


class LockResponse(BaseModel):
    """A single lock record."""

    id: str
    target_type: str
    target_id: str
    target_name: str | None = None
    user_id: str
    username: str
    acquired_at: str
    expires_at: str
    last_heartbeat: str


class LockCheckResponse(BaseModel):
    """Response for checking lock status."""

    locked: bool
    lock: LockResponse | None = None
    is_owner: bool = False


class LockListResponse(BaseModel):
    """List of active locks."""

    items: list[LockResponse]
    total: int
