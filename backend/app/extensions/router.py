"""Extension registry API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import get_current_user
from app.extensions.models import (
    ExtensionInstall,
    ExtensionListResponse,
    ExtensionResponse,
)
from app.extensions.service import (
    disable_extension,
    enable_extension,
    get_extension,
    install_extension,
    list_extensions,
    uninstall_extension,
)

router = APIRouter(prefix="/api/extensions", tags=["extensions"])


@router.get("", response_model=ExtensionListResponse)
async def list_all(
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ExtensionListResponse:
    """List all installed extensions."""
    db = request.app.state.db_manager.main_db
    items = await list_extensions(db)
    return ExtensionListResponse(items=[ExtensionResponse(**item) for item in items])


@router.get("/{extension_id}", response_model=ExtensionResponse)
async def get_one(
    extension_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ExtensionResponse:
    """Get a single extension by ID."""
    db = request.app.state.db_manager.main_db
    result = await get_extension(db, extension_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Extension not found")
    return ExtensionResponse(**result)


@router.post("/{extension_id}/install", response_model=ExtensionResponse, status_code=201)
async def install(
    extension_id: str,
    body: ExtensionInstall,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ExtensionResponse:
    """Install an extension."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    db = request.app.state.db_manager.main_db

    # Check if already installed
    existing = await get_extension(db, extension_id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Extension already installed")

    try:
        result = await install_extension(
            db,
            extension_id=extension_id,
            name=body.name,
            description=body.description,
            version=body.version,
            installed_by=current_user["id"],
            config=body.config,
        )
    except Exception as exc:
        raise HTTPException(  # noqa: B904
            status_code=409,
            detail=f"Failed to install extension: {exc}",
        )

    # Seed demo data for known extensions
    if extension_id == "scenia":
        from app.seed.scenia_seed import seed_scenia_data  # noqa: PLC0415

        await seed_scenia_data(db)

    return ExtensionResponse(**result)


@router.post("/{extension_id}/uninstall", status_code=204)
async def uninstall(
    extension_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Uninstall an extension."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    db = request.app.state.db_manager.main_db

    # Clean up seed data for known extensions
    if extension_id == "scenia":
        from app.seed.scenia_seed import remove_scenia_seed_data  # noqa: PLC0415

        await remove_scenia_seed_data(db)

    removed = await uninstall_extension(db, extension_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Extension not found")


@router.post("/{extension_id}/enable", response_model=ExtensionResponse)
async def enable(
    extension_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ExtensionResponse:
    """Enable an extension."""
    db = request.app.state.db_manager.main_db
    result = await enable_extension(db, extension_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Extension not found")
    return ExtensionResponse(**result)


@router.post("/{extension_id}/disable", response_model=ExtensionResponse)
async def disable(
    extension_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ExtensionResponse:
    """Disable an extension."""
    db = request.app.state.db_manager.main_db
    result = await disable_extension(db, extension_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Extension not found")
    return ExtensionResponse(**result)
