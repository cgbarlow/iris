"""Entity image attachment API routes (ADR-209, v6.17.0).

Routes:
- POST   /api/{entity_type}/{entity_id}/images         (multipart, upload + attach)
- POST   /api/{entity_type}/{entity_id}/images/attach  (JSON, attach existing image)
- GET    /api/{entity_type}/{entity_id}/images
- DELETE /api/{entity_type}/{entity_id}/images/{attachment_id}

`entity_type` ∈ collection | set | package | diagram | element.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from app.auth.dependencies import get_current_user, get_optional_user
from app.images import service as image_service
from app.images.entity_attachment_service import (
    ALLOWED_ENTITY_TYPES,
    AttachmentNotFoundError,
    EntityNotFoundError,
    EntityType,
    ImageNotFoundError,
    attach_image,
    detach_image,
    list_entity_images,
)

router = APIRouter(tags=["images"])

# FastAPI path-validation for the entity_type segment.
EntityTypePath = Literal["collection", "set", "package", "diagram", "element"]


class AttachImageRequest(BaseModel):
    """JSON body for POST .../images/attach — attach an existing image."""

    image_id: str


class EntityImageResponse(BaseModel):
    """One attachment row (joined with image metadata)."""

    id: str
    entity_type: str
    entity_id: str
    image_id: str
    display_order: int
    created_at: str
    created_by: str
    image_mime: str
    image_size_bytes: int


def _check_entity_type(entity_type: str) -> EntityType:
    if entity_type not in ALLOWED_ENTITY_TYPES:
        raise HTTPException(
            status_code=422,
            detail=(
                "entity_type must be one of: "
                + ", ".join(sorted(ALLOWED_ENTITY_TYPES))
            ),
        )
    return entity_type  # type: ignore[return-value]


@router.post(
    "/api/{entity_type}/{entity_id}/images",
    response_model=EntityImageResponse,
    status_code=201,
)
async def upload_and_attach(
    entity_type: EntityTypePath,
    entity_id: str,
    request: Request,
    file: UploadFile = File(...),  # noqa: B008
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> EntityImageResponse:
    """Upload a new image and attach it to the entity in one request.

    Convenience for the UI's "Upload" button. Uses the same validation
    as POST /api/images.
    """
    et = _check_entity_type(entity_type)
    db = request.app.state.db_manager.main_db

    data = await file.read()
    declared = file.content_type or "application/octet-stream"
    try:
        img = await image_service.create_image(
            db, data=data, declared_mime=declared,
            uploaded_by=current_user.get("id"),
        )
    except ValueError as exc:
        msg = str(exc)
        if "exceeds" in msg.lower():
            raise HTTPException(status_code=413, detail=msg) from exc
        raise HTTPException(status_code=400, detail=msg) from exc

    try:
        attachment = await attach_image(
            db, entity_type=et, entity_id=entity_id,
            image_id=str(img["id"]), created_by=current_user.get("id") or "",
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ImageNotFoundError as exc:
        # Shouldn't happen — we just created it.
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        # v6.17.1: most common cause is the Supabase mirror not yet applied —
        # `entity_images` table doesn't exist. Surface the real error so the
        # CORS middleware decorates the response (raising an unhandled
        # exception inside the service can produce a 500 without CORS
        # headers, which the browser then reports as a confusing CORS error).
        import logging  # noqa: PLC0415
        logging.getLogger(__name__).exception("attach_image failed: %s", exc)
        msg = str(exc) or type(exc).__name__
        raise HTTPException(  # noqa: B904
            status_code=503,
            detail=(
                f"Image attachment service unavailable "
                f"({type(exc).__name__}: {msg}). If this just deployed, "
                "the operator may need to run scripts/supabase-migrate.sh "
                "to apply migration m078."
            ),
        )
    return EntityImageResponse(**attachment)


@router.post(
    "/api/{entity_type}/{entity_id}/images/attach",
    response_model=EntityImageResponse,
    status_code=201,
)
async def attach_existing(
    entity_type: EntityTypePath,
    entity_id: str,
    body: AttachImageRequest,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> EntityImageResponse:
    """Attach an existing image (by image_id) to the entity. Used by
    MCP / CLI / cross-entity re-use flows."""
    et = _check_entity_type(entity_type)
    db = request.app.state.db_manager.main_db
    try:
        attachment = await attach_image(
            db, entity_type=et, entity_id=entity_id,
            image_id=body.image_id, created_by=current_user.get("id") or "",
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ImageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        # v6.17.1: graceful 503 when the entity_images table is missing
        # (Supabase migration m078 not yet applied) so CORS headers
        # decorate the response and the real error surfaces to DevTools.
        import logging  # noqa: PLC0415
        logging.getLogger(__name__).exception("attach_image failed: %s", exc)
        msg = str(exc) or type(exc).__name__
        raise HTTPException(  # noqa: B904
            status_code=503,
            detail=(
                f"Image attachment service unavailable "
                f"({type(exc).__name__}: {msg})."
            ),
        )
    return EntityImageResponse(**attachment)


@router.get(
    "/api/{entity_type}/{entity_id}/images",
    response_model=list[EntityImageResponse],
)
async def list_attachments(
    entity_type: EntityTypePath,
    entity_id: str,
    request: Request,
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> list[EntityImageResponse]:
    """List image attachments for the entity. Anon-readable so embedded
    `<img>` tags resolve in MarkdownView without auth."""
    et = _check_entity_type(entity_type)
    db = request.app.state.db_manager.main_db
    try:
        rows = await list_entity_images(db, entity_type=et, entity_id=entity_id)
    except Exception as exc:
        # v6.17.1: graceful 503 on missing table (see attach_existing).
        import logging  # noqa: PLC0415
        logging.getLogger(__name__).exception("list_entity_images failed: %s", exc)
        msg = str(exc) or type(exc).__name__
        raise HTTPException(  # noqa: B904
            status_code=503,
            detail=(
                f"Image attachment service unavailable "
                f"({type(exc).__name__}: {msg})."
            ),
        )
    return [EntityImageResponse(**r) for r in rows]


@router.delete(
    "/api/{entity_type}/{entity_id}/images/{attachment_id}",
    status_code=204,
)
async def detach(
    entity_type: EntityTypePath,
    entity_id: str,
    attachment_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Detach the image from the entity. Does NOT delete the underlying
    image — other entities may reference it."""
    et = _check_entity_type(entity_type)
    db = request.app.state.db_manager.main_db
    try:
        await detach_image(
            db, entity_type=et, entity_id=entity_id, attachment_id=attachment_id,
        )
    except AttachmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
