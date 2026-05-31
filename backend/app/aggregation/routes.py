"""Aggregation REST endpoints (ADR-212, SPEC-212-c)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.aggregation import engine as _engine
from app.aggregation.exceptions import (
    AggregationProfileInvalid,
    AggregationProfileNotFound,
    AggregationProfileScopeError,
    AggregationSourceNotFound,
)
from app.aggregation.models import (
    AggregationProfileCreate,
    AggregationProfileListResponse,
    AggregationProfileResponse,
    AggregationProfileUpdate,
    AggregationResult,
    AggregationRunRequest,
)
from app.aggregation.profiles_service import (
    create_aggregation_profile,
    delete_aggregation_profile,
    get_aggregation_profile,
    list_aggregation_profiles,
    update_aggregation_profile,
)
from app.auth.dependencies import get_current_user, get_optional_user

router = APIRouter(prefix="/api/aggregation", tags=["aggregation"])


# ── Profile CRUD ──────────────────────────────────────────────────────


@router.post(
    "/profiles",
    response_model=AggregationProfileResponse,
    status_code=201,
)
async def create(
    body: AggregationProfileCreate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> AggregationProfileResponse:
    """Create an aggregation profile."""
    db = request.app.state.db_manager.main_db
    try:
        result = await create_aggregation_profile(
            db,
            name=body.name,
            description=body.description,
            set_id=body.set_id,
            is_global=body.is_global,
            profile_data=body.profile_data.model_dump(),
            is_default_for_set=body.is_default_for_set,
            created_by=current_user["id"],
        )
    except AggregationProfileScopeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))  # noqa: B904
    except AggregationProfileInvalid as exc:
        raise HTTPException(status_code=422, detail=str(exc))  # noqa: B904
    return AggregationProfileResponse(**result)


@router.get("/profiles", response_model=AggregationProfileListResponse)
async def list_all(
    request: Request,
    set_id: str | None = None,
    include_global: bool = True,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> AggregationProfileListResponse:
    """List in-scope aggregation profiles."""
    db = request.app.state.db_manager.main_db
    items, total = await list_aggregation_profiles(
        db,
        set_id=set_id,
        include_global=include_global,
        page=page,
        page_size=page_size,
    )
    return AggregationProfileListResponse(
        items=[AggregationProfileResponse(**i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/profiles/{profile_id}", response_model=AggregationProfileResponse,
)
async def get_one(
    profile_id: str,
    request: Request,
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> AggregationProfileResponse:
    """Fetch a single profile."""
    db = request.app.state.db_manager.main_db
    result = await get_aggregation_profile(db, profile_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return AggregationProfileResponse(**result)


@router.put(
    "/profiles/{profile_id}", response_model=AggregationProfileResponse,
)
async def update(
    profile_id: str,
    body: AggregationProfileUpdate,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> AggregationProfileResponse:
    """Edit a profile."""
    db = request.app.state.db_manager.main_db
    raw = body.model_dump(exclude_unset=True)
    kwargs: dict[str, Any] = {}
    if "name" in raw:
        kwargs["name"] = raw["name"]
    if "description" in raw:
        kwargs["description"] = raw["description"]
    if "is_global" in raw:
        kwargs["is_global"] = raw["is_global"]
    if "set_id" in raw:
        kwargs["set_id"] = raw["set_id"]  # may be None
    if "profile_data" in raw:
        kwargs["profile_data"] = raw["profile_data"]
    if "is_default_for_set" in raw:
        kwargs["is_default_for_set"] = raw["is_default_for_set"]
    try:
        result = await update_aggregation_profile(db, profile_id, **kwargs)
    except AggregationProfileScopeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))  # noqa: B904
    except AggregationProfileInvalid as exc:
        raise HTTPException(status_code=422, detail=str(exc))  # noqa: B904
    if result is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return AggregationProfileResponse(**result)


@router.delete("/profiles/{profile_id}", status_code=204)
async def delete(
    profile_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Soft-delete a profile."""
    db = request.app.state.db_manager.main_db
    ok = await delete_aggregation_profile(db, profile_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Profile not found")


# ── Run (read-shaped despite POST) ─────────────────────────────────────


@router.post("/run", response_model=AggregationResult)
async def run_aggregation(
    body: AggregationRunRequest,
    request: Request,
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> AggregationResult:
    """Apply a profile to a source smart-markdown diagram. Returns the
    computed markdown and observed source versions.

    Accepts either ``profile_id`` (saved profile) or ``profile_data``
    (inline draft for the form-editor live preview — SPEC-212-f).
    Exactly one must be provided.
    """
    if body.profile_id and body.profile_data is not None:
        raise HTTPException(
            status_code=400,
            detail="Provide exactly one of profile_id or profile_data",
        )
    if not body.profile_id and body.profile_data is None:
        raise HTTPException(
            status_code=400,
            detail="Provide one of profile_id or profile_data",
        )
    db = request.app.state.db_manager.main_db
    try:
        return await _engine.run(
            db,
            profile_id=body.profile_id,
            profile_data=body.profile_data,
            source_diagram_id=body.source_diagram_id,
        )
    except AggregationProfileNotFound:
        raise HTTPException(  # noqa: B904
            status_code=404, detail="Profile not found",
        )
    except AggregationSourceNotFound:
        raise HTTPException(  # noqa: B904
            status_code=404, detail="Source diagram not found",
        )
