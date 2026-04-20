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

    # Post-install hooks for known extensions
    if extension_id == "scenia":
        from app.seed.scenia_seed import seed_scenia_data  # noqa: PLC0415

        await seed_scenia_data(db)

    if extension_id == "mnemos":
        from app.mnemos.setup import ensure_sdk_importable, start_container  # noqa: PLC0415

        ensure_sdk_importable()
        ok, msg = await start_container()
        if not ok:
            print(f"[MNEMOS] Warning: {msg}", flush=True)
        else:
            # Background reindex so the fresh index has data
            import asyncio  # noqa: PLC0415

            from app.mnemos.sync import background_reindex  # noqa: PLC0415

            asyncio.create_task(background_reindex(db))

    if extension_id == "docref":
        from app.docref.service import refresh_document_index  # noqa: PLC0415

        try:
            refresh_result = await refresh_document_index(db)
            print(
                f"[DocRef] Index populated: {refresh_result['documents_found']} documents found",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[DocRef] Warning: index refresh failed: {exc}", flush=True)

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

    # Pre-uninstall hooks for known extensions
    if extension_id == "scenia":
        from app.seed.scenia_seed import remove_scenia_seed_data  # noqa: PLC0415

        try:
            await remove_scenia_seed_data(db)
        except Exception as exc:
            raise HTTPException(  # noqa: B904
                status_code=500,
                detail=f"Failed to clean up seed data: {exc}",
            )

    if extension_id == "mnemos":
        from app.mnemos.setup import stop_container  # noqa: PLC0415

        ok, msg = await stop_container()
        if not ok:
            print(f"[MNEMOS] Warning during uninstall: {msg}", flush=True)

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

    # Background reindex when MNEMOS is re-enabled
    if extension_id == "mnemos":
        import asyncio  # noqa: PLC0415

        from app.mnemos.sync import background_reindex  # noqa: PLC0415

        asyncio.create_task(background_reindex(db))

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
