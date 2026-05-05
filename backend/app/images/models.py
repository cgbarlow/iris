"""Pydantic models for the images module (ADR-145, v5.4.0)."""

from __future__ import annotations

from pydantic import BaseModel


class ImageUploadResponse(BaseModel):
    """Response after a successful POST /api/images upload."""

    id: str
    mime: str
    size_bytes: int
    created_at: str
