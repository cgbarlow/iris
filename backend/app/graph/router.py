"""Graph API routes per SPEC-116-A, SPEC-117-A."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import get_current_user, get_optional_user
from app.graph.models import GraphResponse, GraphSettingsResponse, GraphSettingsUpdate
from app.graph.service import (
    get_graph_data,
    get_graph_settings_cascaded,
    update_graph_settings,
)

router = APIRouter(prefix="/api/graph", tags=["graph"])


def _require_admin(current_user: dict[str, Any]) -> None:
    """Raise 403 if not admin."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("", response_model=GraphResponse)
async def get_graph(
    request: Request,
    set_id: str | None = None,
    collection_id: str | None = None,
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> GraphResponse:
    """Return knowledge graph data. Scoped to set, collection, or full repository."""
    db = request.app.state.db_manager.main_db
    data = await get_graph_data(
        db, set_id=set_id, collection_id=collection_id,
    )
    return GraphResponse(**data)


@router.get("/settings", response_model=GraphSettingsResponse)
async def get_graph_settings_endpoint(
    request: Request,
    set_id: str | None = None,
    collection_id: str | None = None,
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> GraphSettingsResponse:
    """Return cascaded admin-default graph settings."""
    db = request.app.state.db_manager.main_db
    data = await get_graph_settings_cascaded(
        db, set_id=set_id, collection_id=collection_id,
    )
    return GraphSettingsResponse(**data)


@router.put("/settings", response_model=GraphSettingsResponse)
async def update_graph_settings_endpoint(
    body: GraphSettingsUpdate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> GraphSettingsResponse:
    """Update admin-default graph settings for a scope. Requires admin role."""
    _require_admin(current_user)
    db = request.app.state.db_manager.main_db
    data = await update_graph_settings(
        db,
        scope_type=body.scope_type,
        scope_id=body.scope_id,
        settings=body.settings.model_dump(),
        updated_by=current_user["id"],
    )
    return GraphSettingsResponse(**data)
