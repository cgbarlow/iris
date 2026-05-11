"""Scope-prompt index API (ADR-152, SPEC-152-A).

Single endpoint consumed by the Iris MCP server to populate the
spec-defined `prompts/list` + `prompts/get` capability. Anonymous-
readable, same posture as `list_collections` / `list_sets`.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import get_optional_user
from app.prompts.models import ScopePromptIndexEntry, ScopePromptIndexResponse
from app.prompts.service import list_scope_prompts

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


@router.get("/scope-index", response_model=ScopePromptIndexResponse)
async def scope_index(
    request: Request,
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> ScopePromptIndexResponse:
    """Return one entry per Collection / Set with a non-empty system_prompt."""
    db = request.app.state.db_manager.main_db
    items = await list_scope_prompts(db)
    return ScopePromptIndexResponse(
        items=[ScopePromptIndexEntry(**item) for item in items],
    )
