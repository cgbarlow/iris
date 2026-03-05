"""Recycle bin API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.auth.dependencies import get_current_user
from app.diagrams.service import restore_diagram
from app.elements.service import restore_element
from app.packages.service import restore_package
from app.recycle_bin.models import DeletedItemListResponse, DeletedItemResponse
from app.recycle_bin.service import (
    cascade_restore_by_group,
    empty_recycle_bin,
    hard_delete_item,
    list_deleted_items,
)

router = APIRouter(prefix="/api/recycle-bin", tags=["recycle-bin"])


@router.get("", response_model=DeletedItemListResponse)
async def list_items(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> DeletedItemListResponse:
    """List all soft-deleted items."""
    db = request.app.state.db_manager.main_db
    items, total = await list_deleted_items(db, page=page, page_size=page_size)
    return DeletedItemListResponse(
        items=[DeletedItemResponse(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/packages/{package_id}/restore")
async def restore_package_item(
    package_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, str]:
    """Restore a soft-deleted package."""
    db = request.app.state.db_manager.main_db
    restored = await restore_package(db, package_id, restored_by=current_user["id"])
    if not restored:
        raise HTTPException(status_code=404, detail="Deleted package not found")
    return {"status": "restored", "id": package_id}


@router.post("/diagrams/{diagram_id}/restore")
async def restore_diagram_item(
    diagram_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, str]:
    """Restore a soft-deleted diagram."""
    db = request.app.state.db_manager.main_db
    restored = await restore_diagram(db, diagram_id, restored_by=current_user["id"])
    if not restored:
        raise HTTPException(status_code=404, detail="Deleted diagram not found")
    return {"status": "restored", "id": diagram_id}


@router.post("/elements/{element_id}/restore")
async def restore_element_item(
    element_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, str]:
    """Restore a soft-deleted element."""
    db = request.app.state.db_manager.main_db
    restored = await restore_element(db, element_id, restored_by=current_user["id"])
    if not restored:
        raise HTTPException(status_code=404, detail="Deleted element not found")
    return {"status": "restored", "id": element_id}


@router.post("/groups/{group_id}/restore")
async def restore_group(
    group_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, object]:
    """Restore all items in a cascade deletion group."""
    db = request.app.state.db_manager.main_db
    count = await cascade_restore_by_group(
        db, group_id, restored_by=current_user["id"],
    )
    if count == 0:
        raise HTTPException(status_code=404, detail="No items found for group")
    return {"status": "restored", "group_id": group_id, "count": count}


@router.delete("", status_code=200)
async def empty_all(
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, object]:
    """Permanently delete all soft-deleted items."""
    db = request.app.state.db_manager.main_db
    count = await empty_recycle_bin(db)
    return {"status": "emptied", "count": count}


@router.delete("/{item_type}/{item_id}", status_code=204)
async def permanently_delete(
    item_type: str,
    item_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Permanently delete a soft-deleted item."""
    if item_type not in ("packages", "diagrams", "elements"):
        raise HTTPException(status_code=400, detail="Invalid item type")
    # Map plural route to singular for service
    type_map = {"packages": "package", "diagrams": "diagram", "elements": "element"}
    db = request.app.state.db_manager.main_db
    deleted = await hard_delete_item(db, type_map[item_type], item_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail="Item not found or not soft-deleted",
        )
