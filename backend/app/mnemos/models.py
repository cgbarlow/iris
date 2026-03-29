"""Pydantic models for MNEMOS extension endpoints (ADR-111)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MnemosConfigUpdate(BaseModel):
    """Request body for updating MNEMOS config."""

    url: str = Field(min_length=1, max_length=500)
    timeout_ms: int = Field(default=5000, ge=1000, le=30000)
    max_results: int = Field(default=50, ge=1, le=200)


class MnemosStatusResponse(BaseModel):
    """Response for MNEMOS status check."""

    enabled: bool
    connected: bool
    url: str | None = None
    error: str | None = None


class MnemosReindexResponse(BaseModel):
    """Response for bulk reindex operation."""

    indexed: int
    errors: int
    duration_ms: int
