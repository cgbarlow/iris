"""Set API routes per ADR-060."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response as FastAPIResponse

from app.auth.dependencies import get_current_user
from app.sets.models import (
    SetCreate,
    SetForceDeleteResponse,
    SetListResponse,
    SetResponse,
    SetUpdate,
)
from app.sets.service import (
    create_set,
    force_delete_set,
    get_set,
    get_set_tags,
    get_set_thumbnail,
    list_sets,
    soft_delete_set,
    store_set_thumbnail_image,
    update_set,
)

router = APIRouter(prefix="/api/sets", tags=["sets"])

_MAX_THUMBNAIL_SIZE = 2 * 1024 * 1024  # 2 MB
_ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg"}


@router.post("", response_model=SetResponse, status_code=201)
async def create(
    body: SetCreate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> SetResponse:
    """Create a new set."""
    db = request.app.state.db_manager.main_db
    try:
        result = await create_set(
            db,
            name=body.name,
            description=body.description,
            created_by=current_user["id"],
        )
    except Exception:
        raise HTTPException(  # noqa: B904
            status_code=409, detail="A set with this name already exists"
        )
    return SetResponse(**result)


@router.get("", response_model=SetListResponse)
async def list_all(
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> SetListResponse:
    """List all sets with model/entity counts."""
    db = request.app.state.db_manager.main_db
    items = await list_sets(db)
    return SetListResponse(items=[SetResponse(**item) for item in items])


@router.get("/{set_id}", response_model=SetResponse)
async def get_one(
    set_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> SetResponse:
    """Get a single set by ID."""
    db = request.app.state.db_manager.main_db
    result = await get_set(db, set_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Set not found")
    return SetResponse(**result)


@router.put("/{set_id}", response_model=SetResponse)
async def update(
    set_id: str,
    body: SetUpdate,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> SetResponse:
    """Update a set's name, description, and thumbnail settings."""
    db = request.app.state.db_manager.main_db
    try:
        result = await update_set(
            db, set_id,
            name=body.name,
            description=body.description,
            thumbnail_source=body.thumbnail_source,
            thumbnail_diagram_id=body.thumbnail_diagram_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        raise HTTPException(  # noqa: B904
            status_code=409, detail="A set with this name already exists"
        )
    if result is None:
        raise HTTPException(status_code=404, detail="Set not found")
    return SetResponse(**result)


@router.delete("/{set_id}", response_model=None)
async def delete(
    set_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
    force: bool = Query(default=False),  # noqa: B008
) -> FastAPIResponse | SetForceDeleteResponse:
    """Soft-delete a set. With force=true, also deletes all contents."""
    db = request.app.state.db_manager.main_db

    if force:
        result = await force_delete_set(db, set_id, deleted_by=current_user["id"])
        if isinstance(result, dict) and "error" in result:
            error = result["error"]
            if error == "default":
                raise HTTPException(
                    status_code=403, detail="Cannot delete the Default set"
                )
            if error == "not_found":
                raise HTTPException(status_code=404, detail="Set not found")
        return SetForceDeleteResponse(**result)

    result = await soft_delete_set(db, set_id)
    if result is not None:
        error = result.get("error")
        if error == "default":
            raise HTTPException(status_code=403, detail="Cannot delete the Default set")
        if error == "non_empty":
            raise HTTPException(
                status_code=409,
                detail="Cannot delete a set that contains models or entities",
            )
        if error == "not_found":
            raise HTTPException(status_code=404, detail="Set not found")
    return FastAPIResponse(status_code=204)


@router.post("/{set_id}/thumbnail", response_model=SetResponse)
async def upload_thumbnail(
    set_id: str,
    file: UploadFile,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> SetResponse:
    """Upload a thumbnail image for a set."""
    db = request.app.state.db_manager.main_db

    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only PNG and JPEG images are accepted",
        )

    image_bytes = await file.read()
    if len(image_bytes) > _MAX_THUMBNAIL_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Thumbnail image must be under 2 MB",
        )

    result = await store_set_thumbnail_image(db, set_id, image_bytes)
    if result is None:
        raise HTTPException(status_code=404, detail="Set not found")
    return SetResponse(**result)


@router.get("/{set_id}/thumbnail")
async def get_thumbnail(
    set_id: str,
    request: Request,
    theme: str = Query(default="dark"),  # noqa: B008
) -> FastAPIResponse:
    """Get the thumbnail image for a set."""
    db = request.app.state.db_manager.main_db
    image_bytes = await get_set_thumbnail(db, set_id, theme=theme)
    if image_bytes is None:
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    # Detect content type from magic bytes
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        content_type = "image/png"
    elif image_bytes[:4] == b"\xff\xd8\xff\xe0" or image_bytes[:4] == b"\xff\xd8\xff\xe1":
        content_type = "image/jpeg"
    else:
        content_type = "image/svg+xml"
    return FastAPIResponse(
        content=image_bytes,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/{set_id}/tags")
async def get_tags(
    set_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[str]:
    """Get all unique tags within a set."""
    db = request.app.state.db_manager.main_db
    # Verify set exists
    s = await get_set(db, set_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Set not found")
    return await get_set_tags(db, set_id)
