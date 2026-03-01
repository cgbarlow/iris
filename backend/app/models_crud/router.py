"""Model API routes per SPEC-003-A."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response as FastAPIResponse

from app.auth.dependencies import get_current_user
from app.models_crud.models import (
    ModelCreate,
    ModelListResponse,
    ModelResponse,
    ModelUpdate,
    ModelVersionResponse,
)
from app.models_crud.service import (
    create_model,
    get_model,
    get_model_versions,
    list_models,
    soft_delete_model,
    update_model,
)
from app.models_crud.thumbnail import get_thumbnail, regenerate_all_thumbnails

router = APIRouter(prefix="/api/models", tags=["models"])
admin_router = APIRouter(prefix="/api/admin", tags=["admin"])


def _require_admin(current_user: dict[str, Any]) -> None:
    """Raise 403 if not admin."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


@admin_router.post("/thumbnails/regenerate")
async def regenerate_thumbnails(
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, int]:
    """Regenerate PNG thumbnails for all models. Requires admin role."""
    _require_admin(current_user)
    db = request.app.state.db_manager.main_db
    count = await regenerate_all_thumbnails(db)
    return {"count": count}


@router.post("", response_model=ModelResponse, status_code=201)
async def create(
    body: ModelCreate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ModelResponse:
    """Create a new model."""
    db = request.app.state.db_manager.main_db
    result = await create_model(
        db,
        model_type=body.model_type,
        name=body.name,
        description=body.description,
        data=body.data,
        created_by=current_user["id"],
    )
    return ModelResponse(**result)


@router.get("", response_model=ModelListResponse)
async def list_all(
    request: Request,
    model_type: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ModelListResponse:
    """List models with optional type filter and pagination."""
    db = request.app.state.db_manager.main_db
    items, total = await list_models(
        db, model_type=model_type, page=page, page_size=page_size,
    )
    return ModelListResponse(
        items=[ModelResponse(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{model_id}", response_model=ModelResponse)
async def get_one(
    model_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ModelResponse:
    """Get a single model by ID."""
    db = request.app.state.db_manager.main_db
    result = await get_model(db, model_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return ModelResponse(**result)


@router.put("/{model_id}", response_model=ModelResponse)
async def update(
    model_id: str,
    body: ModelUpdate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ModelResponse:
    """Update a model with optimistic concurrency."""
    if_match = request.headers.get("If-Match")
    if if_match is None:
        raise HTTPException(
            status_code=428, detail="If-Match header required"
        )
    try:
        expected_version = int(if_match)
    except ValueError:
        raise HTTPException(  # noqa: B904
            status_code=400, detail="If-Match must be an integer version"
        )

    db = request.app.state.db_manager.main_db
    result = await update_model(
        db, model_id,
        name=body.name,
        description=body.description,
        data=body.data,
        change_summary=body.change_summary,
        updated_by=current_user["id"],
        expected_version=expected_version,
    )
    if result is None:
        raise HTTPException(status_code=409, detail="Version conflict")

    model = await get_model(db, model_id)
    return ModelResponse(**model)  # type: ignore[arg-type]


@router.delete("/{model_id}", status_code=204)
async def delete(
    model_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Soft-delete a model."""
    if_match = request.headers.get("If-Match")
    if if_match is None:
        raise HTTPException(
            status_code=428, detail="If-Match header required"
        )
    try:
        expected_version = int(if_match)
    except ValueError:
        raise HTTPException(  # noqa: B904
            status_code=400, detail="If-Match must be an integer version"
        )

    db = request.app.state.db_manager.main_db
    deleted = await soft_delete_model(
        db, model_id,
        deleted_by=current_user["id"],
        expected_version=expected_version,
    )
    if not deleted:
        raise HTTPException(status_code=409, detail="Version conflict or not found")


@router.get(
    "/{model_id}/versions",
    response_model=list[ModelVersionResponse],
)
async def get_versions(
    model_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[ModelVersionResponse]:
    """Get all versions of a model."""
    db = request.app.state.db_manager.main_db
    versions = await get_model_versions(db, model_id)
    if not versions:
        raise HTTPException(status_code=404, detail="Model not found")
    return [ModelVersionResponse(**v) for v in versions]


@router.get("/{model_id}/thumbnail")
async def get_model_thumbnail(
    model_id: str,
    request: Request,
    theme: str = Query(default="dark"),
) -> FastAPIResponse:
    """Get the PNG thumbnail for a model."""
    db = request.app.state.db_manager.main_db
    thumbnail = await get_thumbnail(db, model_id, theme=theme)
    if thumbnail is None:
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    # Detect if it's SVG or PNG by checking magic bytes
    content_type = "image/png" if thumbnail[:8] == b"\x89PNG\r\n\x1a\n" else "image/svg+xml"
    return FastAPIResponse(
        content=thumbnail,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.post("/{model_id}/tags", status_code=201)
async def add_tag(
    model_id: str,
    body: dict[str, Any],
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, str]:
    """Add a tag to a model."""
    db = request.app.state.db_manager.main_db
    tag = body.get("tag", "").strip()
    if not tag or len(tag) > 50:
        raise HTTPException(status_code=400, detail="Tag must be 1-50 characters")
    now = datetime.now(tz=UTC).isoformat()
    try:
        await db.execute(
            "INSERT INTO model_tags (model_id, tag, created_at, created_by) "
            "VALUES (?, ?, ?, ?)",
            (model_id, tag, now, current_user["id"]),
        )
        await db.commit()
    except Exception:
        raise HTTPException(  # noqa: B904
            status_code=409, detail="Tag already exists"
        )
    return {"model_id": model_id, "tag": tag, "created_at": now}


@router.delete("/{model_id}/tags/{tag}")
async def remove_tag(
    model_id: str,
    tag: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, str]:
    """Remove a tag from a model."""
    db = request.app.state.db_manager.main_db
    await db.execute(
        "DELETE FROM model_tags WHERE model_id = ? AND tag = ?",
        (model_id, tag),
    )
    await db.commit()
    return {"status": "ok"}
