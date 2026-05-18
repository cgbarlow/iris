"""Batch operations API routes per ADR-060."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import get_current_user
from app.batch.models import (
    BatchElementsCreate,
    BatchElementsUpdate,
    BatchIds,
    BatchModifySet,
    BatchModifyTags,
    BatchResult,
    BatchResultWithIds,
)
from app.batch.service import (
    batch_clone_elements,
    batch_clone_diagrams,
    batch_create_elements,
    batch_delete_elements,
    batch_delete_diagrams,
    batch_set_elements,
    batch_set_diagrams,
    batch_tags_elements,
    batch_tags_diagrams,
    batch_update_elements,
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


# --- Bulk create / update (v6.10.0, ADR-200, #173 item 6) ---


@router.post("/elements/create", response_model=BatchResultWithIds)
async def create_elements(
    body: BatchElementsCreate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> BatchResultWithIds:
    """Bulk create elements. Per-item failure isolation."""
    db = request.app.state.db_manager.main_db
    items = [el.model_dump() for el in body.elements]
    result = await batch_create_elements(
        db, items, created_by=current_user["id"],
    )
    return BatchResultWithIds(**result)


@router.post("/elements/update", response_model=BatchResultWithIds)
async def update_elements(
    body: BatchElementsUpdate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> BatchResultWithIds:
    """Bulk update elements. Per-item expected_version; per-item failure isolation."""
    db = request.app.state.db_manager.main_db
    # ``exclude_unset`` preserves the tri-state semantics of package_id —
    # only items whose payload explicitly included the key get it forwarded.
    items = [u.model_dump(exclude_unset=True) for u in body.updates]
    result = await batch_update_elements(
        db, items, updated_by=current_user["id"],
    )
    return BatchResultWithIds(**result)
