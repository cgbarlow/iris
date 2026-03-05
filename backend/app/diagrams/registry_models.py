"""Pydantic models for the diagram type/notation registry (ADR-079)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class NotationMapping(BaseModel):
    """A notation available for a diagram type."""

    notation_id: str
    notation_name: str
    is_default: bool = False


class DiagramTypeResponse(BaseModel):
    """A diagram type with its available notations."""

    id: str
    name: str
    description: str | None = None
    display_order: int = 0
    is_active: bool = True
    notations: list[NotationMapping] = Field(default_factory=list)


class NotationResponse(BaseModel):
    """A notation entry."""

    id: str
    name: str
    description: str | None = None
    display_order: int = 0
    is_active: bool = True


class NotationUpdateRequest(BaseModel):
    """Request body for changing a diagram's notation."""

    notation: str = Field(min_length=1)
