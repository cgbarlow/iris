"""Pydantic models for comments."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CommentCreate(BaseModel):
    """Request body for creating a comment."""

    content: str = Field(min_length=1, max_length=10000)


class CommentUpdate(BaseModel):
    """Request body for updating a comment."""

    content: str = Field(min_length=1, max_length=10000)


class CommentResponse(BaseModel):
    """Response for a single comment."""

    id: str
    target_type: str
    target_id: str
    user_id: str
    content: str
    created_at: str
    updated_at: str
