"""Pydantic models for batch operations."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BatchIds(BaseModel):
    """Request body with a list of IDs for batch operations."""

    ids: list[str] = Field(min_length=1, max_length=100)


class BatchModifySet(BaseModel):
    """Request body for batch set reassignment."""

    ids: list[str] = Field(min_length=1, max_length=100)
    set_id: str


class BatchModifyTags(BaseModel):
    """Request body for batch tag modification."""

    ids: list[str] = Field(min_length=1, max_length=100)
    add_tags: list[str] = Field(default_factory=list)
    remove_tags: list[str] = Field(default_factory=list)


class BatchResult(BaseModel):
    """Response for batch operations."""

    succeeded: int = 0
    failed: int = 0
    errors: list[str] = Field(default_factory=list)
