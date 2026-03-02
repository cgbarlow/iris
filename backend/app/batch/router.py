"""Batch operations API routes per ADR-060."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import get_current_user
from app.batch.models import BatchIds, BatchModifySet, BatchModifyTags, BatchResult
from app.batch.service import (
    batch_clone_entities,
    batch_clone_models,
    batch_delete_entities,
    batch_delete_models,
    batch_set_entities,
    batch_set_models,
    batch_tags_entities,
    batch_tags_models,
)

router = APIRouter(prefix="/api/batch", tags=["batch"])


# --- Model batch operations ---


@router.post("/models/delete", response_model=BatchResult)
async def delete_models(
    body: BatchIds,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> BatchResult:
    """Batch soft-delete models."""
    db = request.app.state.db_manager.main_db
    result = await batch_delete_models(db, body.ids, deleted_by=current_user["id"])
    return BatchResult(**result)


@router.post("/models/clone", response_model=BatchResult)
async def clone_models(
    body: BatchIds,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> BatchResult:
    """Batch clone models."""
    db = request.app.state.db_manager.main_db
    result = await batch_clone_models(db, body.ids, cloned_by=current_user["id"])
    return BatchResult(**result)


@router.post("/models/set", response_model=BatchResult)
async def set_models(
    body: BatchModifySet,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> BatchResult:
    """Batch reassign models to a different set."""
    db = request.app.state.db_manager.main_db
    result = await batch_set_models(db, body.ids, set_id=body.set_id)
    return BatchResult(**result)


@router.post("/models/tags", response_model=BatchResult)
async def tags_models(
    body: BatchModifyTags,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> BatchResult:
    """Batch add/remove tags on models."""
    db = request.app.state.db_manager.main_db
    result = await batch_tags_models(
        db, body.ids,
        add_tags=body.add_tags,
        remove_tags=body.remove_tags,
        modified_by=current_user["id"],
    )
    return BatchResult(**result)


# --- Entity batch operations ---


@router.post("/entities/delete", response_model=BatchResult)
async def delete_entities(
    body: BatchIds,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> BatchResult:
    """Batch soft-delete entities."""
    db = request.app.state.db_manager.main_db
    result = await batch_delete_entities(db, body.ids, deleted_by=current_user["id"])
    return BatchResult(**result)


@router.post("/entities/clone", response_model=BatchResult)
async def clone_entities(
    body: BatchIds,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> BatchResult:
    """Batch clone entities."""
    db = request.app.state.db_manager.main_db
    result = await batch_clone_entities(db, body.ids, cloned_by=current_user["id"])
    return BatchResult(**result)


@router.post("/entities/set", response_model=BatchResult)
async def set_entities(
    body: BatchModifySet,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> BatchResult:
    """Batch reassign entities to a different set."""
    db = request.app.state.db_manager.main_db
    result = await batch_set_entities(db, body.ids, set_id=body.set_id)
    return BatchResult(**result)


@router.post("/entities/tags", response_model=BatchResult)
async def tags_entities(
    body: BatchModifyTags,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> BatchResult:
    """Batch add/remove tags on entities."""
    db = request.app.state.db_manager.main_db
    result = await batch_tags_entities(
        db, body.ids,
        add_tags=body.add_tags,
        remove_tags=body.remove_tags,
        modified_by=current_user["id"],
    )
    return BatchResult(**result)
