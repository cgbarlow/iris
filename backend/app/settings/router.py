"""Settings API routes — admin-configurable parameters per SPEC-021-A."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import get_current_user
from app.settings.models import SettingResponse, SettingUpdate
from app.seed.example_models import seed_example_models
from app.settings.service import get_all_settings, get_setting, update_setting

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _require_admin(current_user: dict[str, Any]) -> None:
    """Raise 403 if not admin."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("", response_model=list[SettingResponse])
async def list_settings(
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[SettingResponse]:
    """Get all settings. Requires authentication."""
    db = request.app.state.db_manager.main_db
    settings = await get_all_settings(db)
    return [SettingResponse(**s) for s in settings]


@router.get("/{key}", response_model=SettingResponse)
async def get_setting_by_key(
    key: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> SettingResponse:
    """Get a specific setting."""
    db = request.app.state.db_manager.main_db
    setting = await get_setting(db, key)
    if setting is None:
        raise HTTPException(status_code=404, detail="Setting not found")
    return SettingResponse(**setting)


@router.put("/{key}", response_model=SettingResponse)
async def update_setting_by_key(
    key: str,
    body: SettingUpdate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> SettingResponse:
    """Update a setting. Requires admin role."""
    _require_admin(current_user)
    db = request.app.state.db_manager.main_db
    result = await update_setting(db, key, body.value, current_user["id"])
    if result is None:
        raise HTTPException(status_code=404, detail="Setting not found")
    return SettingResponse(**result)


@router.post("/seed-example-data")
async def seed_example_data(
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, str]:
    """Populate the default set with example diagrams. Requires admin role."""
    import contextlib  # noqa: PLC0415

    _require_admin(current_user)
    db = request.app.state.db_manager.main_db

    from app.db.adapter import SupabaseAdapter  # noqa: PLC0415
    hold_ctx = db.hold_connection() if isinstance(db, SupabaseAdapter) else contextlib.nullcontext()
    async with hold_ctx:
        await seed_example_models(db)
        await db.commit()
    return {"detail": "Example data seeded successfully"}
