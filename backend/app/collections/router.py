"""Collection API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response as FastAPIResponse

from app.auth.dependencies import get_current_user, get_optional_user
from app.authz import assert_unscoped_or_admin, assert_write_allowed
from app.collections.models import (
    CollectionCreate,
    CollectionListResponse,
    CollectionResponse,
    CollectionUpdate,
)
from app.collections.service import (
    create_collection,
    get_collection,
    get_collection_thumbnail,
    list_collections,
    soft_delete_collection,
    store_collection_thumbnail_image,
    update_collection,
)
from app.sets.models import SetListResponse, SetResponse
from app.sets.service import list_sets

router = APIRouter(prefix="/api/collections", tags=["collections"])

_MAX_THUMBNAIL_SIZE = 2 * 1024 * 1024  # 2 MB
_ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg"}


@router.post("", response_model=CollectionResponse, status_code=201)
async def create(
    body: CollectionCreate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> CollectionResponse:
    """Create a new collection."""
    db = request.app.state.db_manager.main_db
    # ADR-237: a scoped user may not create new top-level collections.
    await assert_unscoped_or_admin(db, current_user)
    try:
        result = await create_collection(
            db,
            name=body.name,
            description=body.description,
            created_by=current_user["id"],
        )
    except Exception as exc:
        import logging  # noqa: PLC0415
        logging.getLogger(__name__).exception("Failed to create collection: %s", exc)
        raise HTTPException(  # noqa: B904
            status_code=409, detail=f"A collection with this name already exists ({type(exc).__name__}: {exc})"
        )
    return CollectionResponse(**result)


@router.get("", response_model=CollectionListResponse)
async def list_all(
    request: Request,
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> CollectionListResponse:
    """List all collections with set/diagram/element counts."""
    db = request.app.state.db_manager.main_db
    items = await list_collections(db)
    return CollectionListResponse(items=[CollectionResponse(**item) for item in items])


@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_one(
    collection_id: str,
    request: Request,
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> CollectionResponse:
    """Get a single collection by ID."""
    db = request.app.state.db_manager.main_db
    result = await get_collection(db, collection_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return CollectionResponse(**result)


@router.put("/{collection_id}", response_model=CollectionResponse)
async def update(
    collection_id: str,
    body: CollectionUpdate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> CollectionResponse:
    """Update a collection's name, description, and thumbnail settings."""
    db = request.app.state.db_manager.main_db
    # ADR-237: editing collection metadata is allowed only within write-scope.
    await assert_write_allowed(db, current_user, collection_id)
    try:
        result = await update_collection(
            db, collection_id,
            name=body.name,
            description=body.description,
            thumbnail_source=body.thumbnail_source,
            thumbnail_diagram_id=body.thumbnail_diagram_id,
            system_prompt=body.system_prompt,
            mcp_system_context=body.mcp_system_context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        raise HTTPException(  # noqa: B904
            status_code=409, detail="A collection with this name already exists"
        )
    if result is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return CollectionResponse(**result)


@router.delete("/{collection_id}", response_model=None)
async def delete(
    collection_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> FastAPIResponse:
    """Soft-delete a collection and unlink its sets."""
    db = request.app.state.db_manager.main_db
    # ADR-237: a scoped user may not delete collections, even in-scope ones.
    await assert_unscoped_or_admin(db, current_user)

    result = await soft_delete_collection(db, collection_id)
    if result is not None:
        error = result.get("error")
        if error == "not_found":
            raise HTTPException(status_code=404, detail="Collection not found")
    return FastAPIResponse(status_code=204)


@router.post("/{collection_id}/thumbnail", response_model=CollectionResponse)
async def upload_thumbnail(
    collection_id: str,
    file: UploadFile,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> CollectionResponse:
    """Upload a thumbnail image for a collection."""
    db = request.app.state.db_manager.main_db
    # ADR-237: a thumbnail is collection content — gate by write-scope.
    await assert_write_allowed(db, current_user, collection_id)

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

    result = await store_collection_thumbnail_image(db, collection_id, image_bytes)
    if result is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return CollectionResponse(**result)


@router.get("/{collection_id}/thumbnail")
async def get_thumbnail(
    collection_id: str,
    request: Request,
    theme: str = Query(default="dark"),  # noqa: B008
) -> FastAPIResponse:
    """Get the thumbnail image for a collection."""
    db = request.app.state.db_manager.main_db
    image_bytes = await get_collection_thumbnail(db, collection_id, theme=theme)
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


@router.get("/{collection_id}/sets", response_model=SetListResponse)
async def list_collection_sets(
    collection_id: str,
    request: Request,
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> SetListResponse:
    """List all sets in a collection."""
    db = request.app.state.db_manager.main_db

    # Verify collection exists
    coll = await get_collection(db, collection_id)
    if coll is None:
        raise HTTPException(status_code=404, detail="Collection not found")

    items = await list_sets(db, collection_id=collection_id)
    return SetListResponse(items=[SetResponse(**item) for item in items])
