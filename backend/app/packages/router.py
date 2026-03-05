"""Package API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.auth.dependencies import get_current_user
from app.packages.models import (
    PackageCreate,
    PackageHierarchyNode,
    PackageListResponse,
    PackageResponse,
    PackageUpdate,
    PackageVersionResponse,
)
from app.packages.service import (
    cascade_delete_package,
    count_package_descendants,
    create_package,
    get_package,
    get_package_ancestors,
    get_package_children,
    get_package_hierarchy,
    get_package_versions,
    list_packages,
    set_package_parent,
    update_package,
)

router = APIRouter(prefix="/api/packages", tags=["packages"])


@router.post("", response_model=PackageResponse, status_code=201)
async def create(
    body: PackageCreate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> PackageResponse:
    """Create a new package."""
    db = request.app.state.db_manager.main_db
    result = await create_package(
        db,
        name=body.name,
        description=body.description,
        created_by=current_user["id"],
        parent_package_id=body.parent_package_id,
        set_id=body.set_id,
        metadata=body.metadata,
    )
    return PackageResponse(**result)


@router.get("/hierarchy", response_model=list[PackageHierarchyNode])
async def hierarchy(
    request: Request,
    root_id: str | None = None,
    set_id: str | None = None,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[PackageHierarchyNode]:
    """Get the package hierarchy tree."""
    db = request.app.state.db_manager.main_db
    tree = await get_package_hierarchy(db, root_id=root_id, set_id=set_id)
    return [PackageHierarchyNode(**node) for node in tree]


@router.get("", response_model=PackageListResponse)
async def list_all(
    request: Request,
    set_id: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> PackageListResponse:
    """List packages with optional set filter and pagination."""
    db = request.app.state.db_manager.main_db
    items, total = await list_packages(
        db, set_id=set_id, page=page, page_size=page_size,
    )
    return PackageListResponse(
        items=[PackageResponse(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{package_id}/descendants/count")
async def get_descendant_count(
    package_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, int]:
    """Get counts of descendant packages and diagrams."""
    db = request.app.state.db_manager.main_db
    result = await get_package(db, package_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Package not found")
    return await count_package_descendants(db, package_id)


@router.get("/{package_id}", response_model=PackageResponse)
async def get_one(
    package_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> PackageResponse:
    """Get a single package by ID."""
    db = request.app.state.db_manager.main_db
    result = await get_package(db, package_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Package not found")
    return PackageResponse(**result)


@router.put("/{package_id}", response_model=PackageResponse)
async def update(
    package_id: str,
    body: PackageUpdate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> PackageResponse:
    """Update a package with optimistic concurrency."""
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
    result = await update_package(
        db, package_id,
        name=body.name,
        description=body.description,
        change_summary=body.change_summary,
        updated_by=current_user["id"],
        expected_version=expected_version,
        metadata=body.metadata,
    )
    if result is None:
        raise HTTPException(status_code=409, detail="Version conflict")

    package = await get_package(db, package_id)
    return PackageResponse(**package)  # type: ignore[arg-type]


@router.delete("/{package_id}", status_code=204)
async def delete(
    package_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Soft-delete a package."""
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
    deleted = await cascade_delete_package(
        db, package_id,
        deleted_by=current_user["id"],
        expected_version=expected_version,
    )
    if not deleted:
        raise HTTPException(status_code=409, detail="Version conflict or not found")


@router.get("/{package_id}/ancestors")
async def get_ancestors(
    package_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[dict[str, Any]]:
    """Get ancestor chain for breadcrumb navigation (root first)."""
    db = request.app.state.db_manager.main_db
    return await get_package_ancestors(db, package_id)


@router.get("/{package_id}/children")
async def get_children(
    package_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[dict[str, Any]]:
    """Get direct children of a package."""
    db = request.app.state.db_manager.main_db
    return await get_package_children(db, package_id)


@router.put("/{package_id}/parent")
async def set_parent(
    package_id: str,
    body: dict[str, Any],
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, Any]:
    """Set or unset the parent package."""
    db = request.app.state.db_manager.main_db
    parent_id = body.get("parent_package_id")
    result = await set_package_parent(
        db, package_id, parent_id, updated_by=_current_user["id"],
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Package or parent not found")
    if result.get("error") == "cycle":
        raise HTTPException(
            status_code=400, detail="Cannot set parent: would create a cycle"
        )
    return result


@router.get(
    "/{package_id}/versions",
    response_model=list[PackageVersionResponse],
)
async def get_versions(
    package_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[PackageVersionResponse]:
    """Get all versions of a package."""
    db = request.app.state.db_manager.main_db
    versions = await get_package_versions(db, package_id)
    if not versions:
        raise HTTPException(status_code=404, detail="Package not found")
    return [PackageVersionResponse(**v) for v in versions]
