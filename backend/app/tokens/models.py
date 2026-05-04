"""Pydantic models for Personal Access Tokens (ADR-127, SPEC-127-A)."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — Pydantic needs runtime access to build validators

from pydantic import BaseModel, Field


class TokenCreateRequest(BaseModel):
    """Request body for creating a PAT."""

    name: str = Field(..., min_length=1, max_length=100)
    expires_at: datetime | None = None


class TokenResponse(BaseModel):
    """PAT record as returned from list / get — never includes the secret."""

    id: str
    name: str
    prefix: str
    created_at: str
    last_used_at: str | None = None
    expires_at: str | None = None
    revoked_at: str | None = None


class TokenCreateResponse(TokenResponse):
    """Create-time response — carries the plaintext token exactly once."""

    token: str
