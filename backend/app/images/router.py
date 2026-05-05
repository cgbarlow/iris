"""Image upload + serve API routes (ADR-145, v5.4.0).

Used by the markdown editor's paste-from-clipboard flow. Auth required
on POST (any signed-in user); GET is public so embedded `<img src>`
tags resolve without sending the JWT cookie/header on every render.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response

from app.auth.dependencies import get_current_user
from app.images.models import ImageUploadResponse
from app.images import service

router = APIRouter(prefix="/api/images", tags=["images"])


@router.post(
    "",
    response_model=ImageUploadResponse,
    status_code=201,
)
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> ImageUploadResponse:
    """Upload an image. Used by the markdown editor's paste handler."""
    db = request.app.state.db_manager.main_db
    data = await file.read()
    declared = file.content_type or "application/octet-stream"
    try:
        result = await service.create_image(
            db,
            data=data,
            declared_mime=declared,
            uploaded_by=current_user.get("id"),
        )
    except ValueError as exc:
        # Map upload validation errors to 400 (or 413 for "too large").
        msg = str(exc)
        if "exceeds" in msg.lower():
            raise HTTPException(status_code=413, detail=msg) from exc
        raise HTTPException(status_code=400, detail=msg) from exc
    return ImageUploadResponse(**result)


@router.get("/{image_id}")
async def get_image(image_id: str, request: Request) -> Response:
    """Serve image bytes with the right Content-Type. Public — embedded
    `<img src>` resolves without auth so MarkdownView renders inline.
    The bytes are not user-authored secrets; they're attached to public
    repository content."""
    db = request.app.state.db_manager.main_db
    img = await service.get_image(db, image_id)
    if img is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return Response(
        content=img["bytes"],  # type: ignore[arg-type]
        media_type=str(img["mime"]),
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
