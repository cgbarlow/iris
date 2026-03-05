"""Registry API routes for diagram types and notations (ADR-079)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import get_current_user
from app.diagrams.registry_models import (
    DiagramTypeResponse,
    NotationResponse,
    NotationUpdateRequest,
)
from app.diagrams.registry_service import (
    list_diagram_types,
    list_notations,
    update_diagram_notation,
)

router = APIRouter(prefix="/api/registry", tags=["registry"])


@router.get("/diagram-types", response_model=list[DiagramTypeResponse])
async def get_diagram_types(
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[DiagramTypeResponse]:
    """List all active diagram types with their notation mappings."""
    db = request.app.state.db_manager.main_db
    items = await list_diagram_types(db)
    return [DiagramTypeResponse(**item) for item in items]


@router.get("/notations", response_model=list[NotationResponse])
async def get_notations(
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[NotationResponse]:
    """List all active notations."""
    db = request.app.state.db_manager.main_db
    items = await list_notations(db)
    return [NotationResponse(**item) for item in items]


@router.put("/diagrams/{diagram_id}/notation")
async def change_diagram_notation(
    diagram_id: str,
    body: NotationUpdateRequest,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, str]:
    """Change a diagram's notation."""
    db = request.app.state.db_manager.main_db
    result = await update_diagram_notation(db, diagram_id, body.notation)
    if result is None:
        raise HTTPException(status_code=404, detail="Diagram not found")
    if result.get("error") == "invalid_pair":
        raise HTTPException(
            status_code=400,
            detail="Invalid notation for this diagram type",
        )
    return result
