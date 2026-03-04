"""Batch operations API routes per ADR-060."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import get_current_user
from app.batch.models import BatchIds, BatchModifySet, BatchModifyTags, BatchResult
from app.batch.service import (
    batch_clone_elements,
    batch_clone_diagrams,
    batch_delete_elements,
    batch_delete_diagrams,
    batch_set_elements,
    batch_set_diagrams,
    batch_tags_elements,
    batch_tags_diagrams,
)

router = APIRouter(prefix="/api/batch", tags=["batch"])


# --- Diagram batch operations ---


@router.post("/diagrams/delete", response_model=BatchResult)
async def delete_diagrams(
    body: BatchIds,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> BatchResult:
    """Batch soft-delete diagrams."""
    db = request.app.state.db_manager.main_db
    result = await batch_delete_diagrams(db, body.ids, deleted_by=current_user["id"])
    return BatchResult(**result)


@router.post("/diagrams/clone", response_model=BatchResult)
async def clone_diagrams(
    body: BatchIds,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> BatchResult:
    """Batch clone diagrams."""
    db = request.app.state.db_manager.main_db
    result = await batch_clone_diagrams(db, body.ids, cloned_by=current_user["id"])
    return BatchResult(**result)


@router.post("/diagrams/set", response_model=BatchResult)
async def set_diagrams(
    body: BatchModifySet,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> BatchResult:
    """Batch reassign diagrams to a different set."""
    db = request.app.state.db_manager.main_db
    result = await batch_set_diagrams(db, body.ids, set_id=body.set_id)
    return BatchResult(**result)


@router.post("/diagrams/tags", response_model=BatchResult)
async def tags_diagrams(
    body: BatchModifyTags,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> BatchResult:
    """Batch add/remove tags on diagrams."""
    db = request.app.state.db_manager.main_db
    result = await batch_tags_diagrams(
        db, body.ids,
        add_tags=body.add_tags,
        remove_tags=body.remove_tags,
        modified_by=current_user["id"],
    )
    return BatchResult(**result)


# --- Element batch operations ---


@router.post("/elements/delete", response_model=BatchResult)
async def delete_elements(
    body: BatchIds,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> BatchResult:
    """Batch soft-delete elements."""
    db = request.app.state.db_manager.main_db
    result = await batch_delete_elements(db, body.ids, deleted_by=current_user["id"])
    return BatchResult(**result)


@router.post("/elements/clone", response_model=BatchResult)
async def clone_elements(
    body: BatchIds,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> BatchResult:
    """Batch clone elements."""
    db = request.app.state.db_manager.main_db
    result = await batch_clone_elements(db, body.ids, cloned_by=current_user["id"])
    return BatchResult(**result)


@router.post("/elements/set", response_model=BatchResult)
async def set_elements(
    body: BatchModifySet,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> BatchResult:
    """Batch reassign elements to a different set."""
    db = request.app.state.db_manager.main_db
    result = await batch_set_elements(db, body.ids, set_id=body.set_id)
    return BatchResult(**result)


@router.post("/elements/tags", response_model=BatchResult)
async def tags_elements(
    body: BatchModifyTags,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> BatchResult:
    """Batch add/remove tags on elements."""
    db = request.app.state.db_manager.main_db
    result = await batch_tags_elements(
        db, body.ids,
        add_tags=body.add_tags,
        remove_tags=body.remove_tags,
        modified_by=current_user["id"],
    )
    return BatchResult(**result)
