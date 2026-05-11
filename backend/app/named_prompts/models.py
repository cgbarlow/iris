"""Pydantic models for named-prompts CRUD (ADR-154, SPEC-154-A)."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

NAME_PATTERN = r"^[a-z][a-z0-9-]{0,63}$"
NAME_RE = re.compile(NAME_PATTERN)

_DESCRIPTION_MAX = 1024
_BODY_MAX = 256_000


class Prompt(BaseModel):
    """A named prompt attached to a Collection or Set."""

    id: str
    scope_type: Literal["collection", "set"]
    scope_id: str
    name: str
    description: str
    body: str
    created_at: str
    updated_at: str
    created_by: str | None = None


class PromptCreate(BaseModel):
    """Request body for creating a named prompt."""

    scope_type: Literal["collection", "set"]
    scope_id: str
    name: str = Field(min_length=1, max_length=64, pattern=NAME_PATTERN)
    description: str = Field(min_length=1, max_length=_DESCRIPTION_MAX)
    body: str = Field(min_length=1, max_length=_BODY_MAX)


class PromptUpdate(BaseModel):
    """Request body for updating a named prompt.

    Only description and body are mutable. scope and name are immutable
    post-create; renaming requires delete-and-recreate.
    """

    description: str | None = Field(default=None, min_length=1, max_length=_DESCRIPTION_MAX)
    body: str | None = Field(default=None, min_length=1, max_length=_BODY_MAX)


class PromptListResponse(BaseModel):
    items: list[Prompt]
