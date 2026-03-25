"""Scenia roadmapping API routes — gated on scenia extension."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.auth.dependencies import get_current_user
from app.scenia.dependencies import require_scenia_enabled
from app.scenia.models import (
    AppStatusCreate,
    AppStatusListResponse,
    AppStatusResponse,
    AssetCategoryCreate,
    AssetCategoryListResponse,
    AssetCategoryResponse,
    SceniaBulkData,
    SceniaDependencyCreate,
    SceniaDependencyListResponse,
    SceniaDependencyResponse,
    SceniaEntityCreate,
    SceniaEntityListResponse,
    SceniaEntityResponse,
    SceniaEntityUpdate,
    TimelineSettingsResponse,
    TimelineSettingsUpdate,
    VersionCreate,
    VersionListResponse,
    VersionResponse,
)
from app.scenia.service import (
    ENTITY_TYPES,
    create_app_status,
    create_asset_category,
    create_scenia_dependency,
    create_scenia_entity,
    create_version,
    delete_app_status,
    delete_asset_category,
    delete_scenia_dependency,
    delete_scenia_entity,
    get_bulk_data,
    get_element_scenia_link,
    get_scenia_entity,
    get_timeline_settings,
    list_app_statuses,
    list_asset_categories,
    list_scenia_dependencies,
    list_scenia_entities,
    list_versions,
    save_bulk_data,
    update_scenia_entity,
    upsert_timeline_settings,
)

router = APIRouter(
    prefix="/api/scenia",
    tags=["scenia"],
    dependencies=[Depends(require_scenia_enabled)],
)


# ---------------------------------------------------------------------------
# Bulk data (primary integration point)
# ---------------------------------------------------------------------------


@router.get("/data", response_model=SceniaBulkData)
async def get_data(
    request: Request,
    set_id: str = Query(),  # noqa: B008
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> SceniaBulkData:
    """Get all Scenia data for a set."""
    db = request.app.state.db_manager.main_db
    result = await get_bulk_data(db, set_id)
    return SceniaBulkData(**result)


@router.put("/data", response_model=SceniaBulkData)
async def save_data(
    request: Request,
    set_id: str = Query(),  # noqa: B008
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> SceniaBulkData:
    """Save all Scenia data for a set (atomic write)."""
    db = request.app.state.db_manager.main_db
    body = await request.json()
    result = await save_bulk_data(db, set_id, data=body, saved_by=current_user["id"])
    return SceniaBulkData(**result)


# ---------------------------------------------------------------------------
# Generic entity CRUD factory
# ---------------------------------------------------------------------------


def _make_entity_routes(entity_key: str, element_type: str) -> APIRouter:
    """Create CRUD routes for a Scenia entity type."""
    sub = APIRouter()

    @sub.get(f"/{entity_key}", response_model=SceniaEntityListResponse)
    async def list_entities(
        request: Request,
        set_id: str | None = Query(default=None),  # noqa: B008
        _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
    ) -> SceniaEntityListResponse:
        db = request.app.state.db_manager.main_db
        items = await list_scenia_entities(db, element_type, set_id=set_id)
        return SceniaEntityListResponse(items=[SceniaEntityResponse(**i) for i in items])

    @sub.post(f"/{entity_key}", response_model=SceniaEntityResponse, status_code=201)
    async def create_entity(
        body: SceniaEntityCreate,
        request: Request,
        current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
    ) -> SceniaEntityResponse:
        db = request.app.state.db_manager.main_db
        result = await create_scenia_entity(
            db,
            element_type=element_type,
            name=body.name,
            description=body.description,
            data=body.data,
            set_id=body.set_id,
            created_by=current_user["id"],
        )
        return SceniaEntityResponse(**result)

    @sub.get(f"/{entity_key}/{{entity_id}}", response_model=SceniaEntityResponse)
    async def get_entity(
        entity_id: str,
        request: Request,
        _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
    ) -> SceniaEntityResponse:
        db = request.app.state.db_manager.main_db
        result = await get_scenia_entity(db, entity_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"{entity_key[:-1].title()} not found")
        return SceniaEntityResponse(**result)

    @sub.put(f"/{entity_key}/{{entity_id}}", response_model=SceniaEntityResponse)
    async def update_entity(
        entity_id: str,
        body: SceniaEntityUpdate,
        request: Request,
        current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
    ) -> SceniaEntityResponse:
        db = request.app.state.db_manager.main_db
        result = await update_scenia_entity(
            db, entity_id,
            name=body.name,
            description=body.description,
            data=body.data,
            updated_by=current_user["id"],
        )
        if result is None:
            raise HTTPException(status_code=404, detail=f"{entity_key[:-1].title()} not found")
        return SceniaEntityResponse(**result)

    @sub.delete(f"/{entity_key}/{{entity_id}}", status_code=204)
    async def delete_entity(
        entity_id: str,
        request: Request,
        _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
    ) -> None:
        db = request.app.state.db_manager.main_db
        deleted = await delete_scenia_entity(db, entity_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"{entity_key[:-1].title()} not found")

    return sub


# Register entity routes for each type
for _key, _etype in ENTITY_TYPES.items():
    router.include_router(_make_entity_routes(_key, _etype))


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


@router.get("/dependencies", response_model=SceniaDependencyListResponse)
async def list_deps(
    request: Request,
    set_id: str | None = Query(default=None),  # noqa: B008
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> SceniaDependencyListResponse:
    """List Scenia dependencies."""
    db = request.app.state.db_manager.main_db
    items = await list_scenia_dependencies(db, set_id=set_id)
    return SceniaDependencyListResponse(items=[SceniaDependencyResponse(**i) for i in items])


@router.post("/dependencies", response_model=SceniaDependencyResponse, status_code=201)
async def create_dep(
    body: SceniaDependencyCreate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> SceniaDependencyResponse:
    """Create a Scenia dependency."""
    db = request.app.state.db_manager.main_db
    result = await create_scenia_dependency(
        db,
        source_id=body.source_id,
        target_id=body.target_id,
        dependency_type=body.dependency_type,
        set_id=body.set_id,
        data=body.data,
        created_by=current_user["id"],
    )
    return SceniaDependencyResponse(**result)


@router.delete("/dependencies/{dependency_id}", status_code=204)
async def delete_dep(
    dependency_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Delete a Scenia dependency."""
    db = request.app.state.db_manager.main_db
    deleted = await delete_scenia_dependency(db, dependency_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Dependency not found")


# ---------------------------------------------------------------------------
# Timeline settings
# ---------------------------------------------------------------------------


@router.get("/timeline-settings", response_model=TimelineSettingsResponse | None)
async def get_timeline(
    request: Request,
    set_id: str = Query(),  # noqa: B008
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> TimelineSettingsResponse | None:
    """Get timeline settings for a set."""
    db = request.app.state.db_manager.main_db
    result = await get_timeline_settings(db, set_id)
    if result is None:
        return None
    return TimelineSettingsResponse(**result)


@router.put("/timeline-settings", response_model=TimelineSettingsResponse)
async def save_timeline(
    body: TimelineSettingsUpdate,
    request: Request,
    set_id: str = Query(),  # noqa: B008
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> TimelineSettingsResponse:
    """Create or update timeline settings for a set."""
    db = request.app.state.db_manager.main_db
    result = await upsert_timeline_settings(
        db, set_id,
        start_date=body.start_date,
        end_date=body.end_date,
        view_mode=body.view_mode,
        zoom_level=body.zoom_level,
        data=body.data,
    )
    return TimelineSettingsResponse(**result)


# ---------------------------------------------------------------------------
# Asset categories
# ---------------------------------------------------------------------------


@router.get("/asset-categories", response_model=AssetCategoryListResponse)
async def list_cats(
    request: Request,
    set_id: str = Query(),  # noqa: B008
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> AssetCategoryListResponse:
    """List asset categories for a set."""
    db = request.app.state.db_manager.main_db
    items = await list_asset_categories(db, set_id)
    return AssetCategoryListResponse(items=[AssetCategoryResponse(**i) for i in items])


@router.post("/asset-categories", response_model=AssetCategoryResponse, status_code=201)
async def create_cat(
    body: AssetCategoryCreate,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> AssetCategoryResponse:
    """Create an asset category."""
    db = request.app.state.db_manager.main_db
    result = await create_asset_category(
        db, set_id=body.set_id, name=body.name, color=body.color, display_order=body.display_order,
    )
    return AssetCategoryResponse(**result)


@router.delete("/asset-categories/{category_id}", status_code=204)
async def delete_cat(
    category_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Delete an asset category."""
    db = request.app.state.db_manager.main_db
    deleted = await delete_asset_category(db, category_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Category not found")


# ---------------------------------------------------------------------------
# Application statuses
# ---------------------------------------------------------------------------


@router.get("/app-statuses", response_model=AppStatusListResponse)
async def list_statuses(
    request: Request,
    set_id: str = Query(),  # noqa: B008
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> AppStatusListResponse:
    """List application statuses for a set."""
    db = request.app.state.db_manager.main_db
    items = await list_app_statuses(db, set_id)
    return AppStatusListResponse(items=[AppStatusResponse(**i) for i in items])


@router.post("/app-statuses", response_model=AppStatusResponse, status_code=201)
async def create_status(
    body: AppStatusCreate,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> AppStatusResponse:
    """Create an application status."""
    db = request.app.state.db_manager.main_db
    result = await create_app_status(
        db, set_id=body.set_id, name=body.name, color=body.color, display_order=body.display_order,
    )
    return AppStatusResponse(**result)


@router.delete("/app-statuses/{status_id}", status_code=204)
async def delete_status(
    status_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Delete an application status."""
    db = request.app.state.db_manager.main_db
    deleted = await delete_app_status(db, status_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Status not found")


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------


@router.get("/versions", response_model=VersionListResponse)
async def list_vers(
    request: Request,
    set_id: str = Query(),  # noqa: B008
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> VersionListResponse:
    """List version snapshots for a set."""
    db = request.app.state.db_manager.main_db
    items = await list_versions(db, set_id)
    return VersionListResponse(items=[VersionResponse(**i) for i in items])


@router.post("/versions", response_model=VersionResponse, status_code=201)
async def create_ver(
    body: VersionCreate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> VersionResponse:
    """Create a version snapshot."""
    db = request.app.state.db_manager.main_db
    result = await create_version(
        db, set_id=body.set_id, name=body.name, data=body.data, created_by=current_user["id"],
    )
    return VersionResponse(**result)


# ---------------------------------------------------------------------------
# Cross-link check
# ---------------------------------------------------------------------------


@router.get("/link/{element_id}")
async def check_link(
    element_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, object]:
    """Check if an element has Scenia cross-link info."""
    db = request.app.state.db_manager.main_db
    result = await get_element_scenia_link(db, element_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No Scenia link for this element")
    return result
