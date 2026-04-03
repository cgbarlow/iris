"""Graph API routes per SPEC-116-A."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import get_current_user
from app.graph.models import GraphResponse
from app.graph.service import get_graph_data

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("", response_model=GraphResponse)
async def get_graph(
    request: Request,
    set_id: str | None = None,
    collection_id: str | None = None,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> GraphResponse:
    """Return knowledge graph data. Scoped to set, collection, or full repository."""
    db = request.app.state.db_manager.main_db
    data = await get_graph_data(
        db, set_id=set_id, collection_id=collection_id,
    )
    return GraphResponse(**data)
