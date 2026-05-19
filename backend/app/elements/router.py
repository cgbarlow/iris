"""Element API routes per SPEC-006-A."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.auth.dependencies import get_current_user, get_optional_user
from app.elements.models import (
    ElementCreate,
    ElementListResponse,
    ElementResponse,
    ElementRollback,
    ElementUpdate,
    ElementVersionResponse,
)
from app.elements.models import _UNSET as _ELEMENT_UPDATE_UNSET
from app.element_templates.service import (
    apply_template_to_create_body,
    get_element_template,
)
from app.elements.service import (
    ElementPackageInvariantError,
    cascade_delete_element,
    create_element,
    get_element,
    get_element_version,
    get_element_versions,
    list_elements,
    rollback_element,
    soft_delete_element,
    update_element,
)

router = APIRouter(prefix="/api/elements", tags=["elements"])


@router.post("", response_model=ElementResponse, status_code=201)
async def create(
    body: ElementCreate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ElementResponse:
    """Create a new element. When ``template_id`` is supplied, the
    named template pre-fills whitelisted fields (ADR-191) — explicit
    request fields always win over template defaults.
    """
    db = request.app.state.db_manager.main_db
    fields = body.model_dump(exclude_unset=True)
    template_id = fields.pop("template_id", None)
    template_tags: list[str] = []
    if template_id:
        template = await get_element_template(db, template_id)
        if template is None:
            raise HTTPException(
                status_code=404, detail=f"Template {template_id} not found",
            )
        fields = apply_template_to_create_body(template, fields)
        # Tags are written to a separate table after the element is
        # created; pop them off the create body so they don't reach
        # the service signature.
        template_tags = list(fields.pop("tags", None) or [])

    # Post-merge required-field validation.
    element_type = fields.get("element_type") or ""
    name = fields.get("name") or ""
    if not element_type:
        raise HTTPException(
            status_code=422,
            detail="element_type is required (provide explicitly or via template)",
        )
    if not name:
        raise HTTPException(
            status_code=422,
            detail="name is required (provide explicitly or via template)",
        )

    try:
        result = await create_element(
            db,
            element_type=element_type,
            name=name,
            description=fields.get("description"),
            data=fields.get("data") or {},
            created_by=current_user["id"],
            set_id=fields.get("set_id"),
            package_id=fields.get("package_id"),
            metadata=fields.get("metadata"),
            notation=fields.get("notation") or "simple",
        )
    except ElementPackageInvariantError as exc:
        raise HTTPException(status_code=422, detail=str(exc))  # noqa: B904

    # Apply template-supplied tags (if any) to the element_tags table.
    if template_tags:
        now = datetime.now(tz=UTC).isoformat()
        for tag in template_tags:
            tag = str(tag).strip()
            if not tag or len(tag) > 50:
                continue
            try:
                await db.execute(
                    "INSERT INTO element_tags (element_id, tag, "
                    "created_at, created_by) VALUES (?, ?, ?, ?)",
                    (result["id"], tag, now, current_user["id"]),
                )
            except Exception:
                # Tag already exists — skip silently.
                pass
        await db.commit()

    # Re-read so we pick up package_name/set_name without re-issuing joins
    # in the create path.
    fresh = await get_element(db, result["id"])
    return ElementResponse(**(fresh or result))


@router.get("", response_model=ElementListResponse)
async def list_all(
    request: Request,
    element_type: str | None = None,
    set_id: str | None = None,
    collection_id: str | None = None,
    package_id: str | None = None,
    notation: str | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> ElementListResponse:
    """List elements with optional filters and pagination.

    ``package_id`` accepts the three-valued sentinel (ADR-185): omit the
    parameter, pass the literal string ``"null"``, or pass a UUID.
    """
    db = request.app.state.db_manager.main_db
    items, total = await list_elements(
        db,
        element_type=element_type,
        set_id=set_id,
        collection_id=collection_id,
        package_id=package_id,
        notation=notation,
        search=search,
        page=page,
        page_size=page_size,
    )
    return ElementListResponse(
        items=[ElementResponse(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/tags/all")
async def list_all_tags(
    request: Request,
    set_id: str | None = None,
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> list[str]:
    """List all unique tags from elements and diagrams, optionally scoped by set."""
    db = request.app.state.db_manager.main_db
    if set_id:
        cursor = await db.execute(
            "SELECT DISTINCT tag FROM ("
            "  SELECT et.tag FROM element_tags et"
            "  JOIN elements e ON et.element_id = e.id"
            "  WHERE e.set_id = ? AND e.is_deleted = 0"
            "  UNION"
            "  SELECT dt.tag FROM diagram_tags dt"
            "  JOIN diagrams d ON dt.diagram_id = d.id"
            "  WHERE d.set_id = ? AND d.is_deleted = 0"
            ") ORDER BY tag",
            (set_id, set_id),
        )
    else:
        cursor = await db.execute(
            "SELECT DISTINCT tag FROM ("
            "  SELECT tag FROM element_tags"
            "  UNION"
            "  SELECT tag FROM diagram_tags"
            ") ORDER BY tag"
        )
    rows = await cursor.fetchall()
    return [row[0] for row in rows]


@router.get("/{element_id}", response_model=ElementResponse)
async def get_one(
    element_id: str,
    request: Request,
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> ElementResponse:
    """Get a single element by ID."""
    db = request.app.state.db_manager.main_db
    result = await get_element(db, element_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Element not found")
    return ElementResponse(**result)


@router.get("/{element_id}/attribute-keys", response_model=list[str])
async def get_attribute_keys(
    element_id: str,
    request: Request,
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> list[str]:
    """Return the sorted list of keys in this element's ``data`` JSON.

    ADR-205 (v6.14.0): drives the Smart Markdown picker's field step
    so the user can insert an ``attr:<key>`` token referencing a
    custom attribute of the selected element. Returns an empty list
    if ``data`` is null, missing, or not a dict. 404 if the element
    doesn't exist or is deleted.

    ADR-206 (v6.15.0): superseded by ``/data-tree`` for the new
    drill UI; this endpoint is retained for backwards compat with
    any cached v6.14.x frontend.
    """
    db = request.app.state.db_manager.main_db
    elem = await get_element(db, element_id)
    if elem is None:
        raise HTTPException(status_code=404, detail="Element not found")
    data = elem.get("data")
    if not isinstance(data, dict):
        return []
    return sorted(str(k) for k in data.keys())


def _describe_node(node: Any) -> dict[str, Any]:
    """Return the tree-descriptor for a node (ADR-206).

    Shapes (one of):
      {"kind": "dict",          "keys":  [...]}
      {"kind": "list_of_named", "names": [...]}
      {"kind": "list",          "length": N}
      {"kind": "primitive",     "value": "..."}
      {"kind": "empty"}             # node is None
    """
    if node is None:
        return {"kind": "empty"}
    if isinstance(node, dict):
        return {"kind": "dict", "keys": sorted(str(k) for k in node.keys())}
    if isinstance(node, list):
        if node and all(
            isinstance(item, dict) and "name" in item for item in node
        ):
            return {
                "kind": "list_of_named",
                "names": [str(item.get("name", "")) for item in node],
            }
        return {"kind": "list", "length": len(node)}
    # primitive
    return {"kind": "primitive", "value": str(node)}


def _walk_node(node: Any, segments: list[str]) -> Any | None:
    """Walk along segments using the same rules as the resolver
    (ADR-206 `_resolve_attr_path`)."""
    for seg in segments:
        if isinstance(node, dict):
            if seg in node:
                node = node[seg]
                continue
            return None
        if isinstance(node, list):
            if seg.isdigit():
                idx = int(seg)
                if 0 <= idx < len(node):
                    node = node[idx]
                    continue
                return None
            if node and all(
                isinstance(item, dict) and "name" in item for item in node
            ):
                match = next(
                    (item for item in node if item.get("name") == seg), None,
                )
                if match is None:
                    return None
                node = match
                continue
            return None
        # primitive but more segments remain
        return None
    return node


_NODE_NOT_FOUND = object()


@router.get("/{element_id}/data-tree")
async def get_data_tree(
    element_id: str,
    request: Request,
    path: str | None = Query(default=None),
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> dict[str, Any]:
    """Tree descriptor for the Smart Markdown picker drill UI (ADR-206).

    Walks ``element.data`` along ``path`` (optional, ``/``-separated
    using the same lookup rules as the resolver: dict-key, numeric
    index, or named-array-lookup for arrays of dicts with a ``name``
    field). Returns a single-level descriptor of the resolved node.

    404 if the element is missing/deleted, or if the path doesn't
    resolve. Path = empty / omitted → descriptor of the root.
    """
    db = request.app.state.db_manager.main_db
    elem = await get_element(db, element_id)
    if elem is None:
        raise HTTPException(status_code=404, detail="Element not found")
    data = elem.get("data")
    segments = [s for s in (path or "").split("/") if s] if path else []
    if not segments:
        return _describe_node(data if data is not None else None)
    if not isinstance(data, dict):
        raise HTTPException(status_code=404, detail="Path not found")
    node = _walk_node(data, segments)
    if node is None:
        raise HTTPException(status_code=404, detail="Path not found")
    return _describe_node(node)


@router.put("/{element_id}", response_model=ElementResponse)
async def update(
    element_id: str,
    body: ElementUpdate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ElementResponse:
    """Update an element with optimistic concurrency (If-Match header)."""
    if_match = request.headers.get("If-Match")
    if if_match is None:
        raise HTTPException(
            status_code=428, detail="If-Match header required for updates"
        )
    try:
        expected_version = int(if_match)
    except ValueError:
        raise HTTPException(  # noqa: B904
            status_code=400, detail="If-Match must be an integer version"
        )

    db = request.app.state.db_manager.main_db
    # ElementUpdate's ``package_id`` defaults to the _UNSET sentinel
    # (meaning "do not touch"); the service layer treats an explicit
    # ``None`` as "clear". Forward as-is via the same sentinel.
    update_kwargs: dict[str, Any] = {
        "name": body.name,
        "description": body.description,
        "data": body.data,
        "change_summary": body.change_summary,
        "updated_by": current_user["id"],
        "expected_version": expected_version,
        "metadata": body.metadata,
    }
    if body.package_id is not _ELEMENT_UPDATE_UNSET:
        update_kwargs["package_id"] = body.package_id
    try:
        result = await update_element(db, element_id, **update_kwargs)
    except ElementPackageInvariantError as exc:
        raise HTTPException(status_code=422, detail=str(exc))  # noqa: B904
    if result is None:
        raise HTTPException(status_code=409, detail="Version conflict")

    element = await get_element(db, element_id)
    return ElementResponse(**element)  # type: ignore[arg-type]


@router.post("/{element_id}/rollback", response_model=ElementResponse)
async def rollback(
    element_id: str,
    body: ElementRollback,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ElementResponse:
    """Rollback an element to a previous version."""
    if_match = request.headers.get("If-Match")
    if if_match is None:
        raise HTTPException(
            status_code=428, detail="If-Match header required for rollback"
        )
    try:
        expected_version = int(if_match)
    except ValueError:
        raise HTTPException(  # noqa: B904
            status_code=400, detail="If-Match must be an integer version"
        )

    db = request.app.state.db_manager.main_db
    result = await rollback_element(
        db,
        element_id,
        target_version=body.target_version,
        rolled_back_by=current_user["id"],
        expected_version=expected_version,
    )
    if result is None:
        raise HTTPException(status_code=409, detail="Version conflict or not found")

    element = await get_element(db, element_id)
    return ElementResponse(**element)  # type: ignore[arg-type]


@router.delete("/{element_id}", status_code=204)
async def delete(
    element_id: str,
    request: Request,
    cascade: bool = False,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> None:
    """Soft-delete an element. With cascade=true, also removes from all diagram canvases and deletes relationships."""
    if_match = request.headers.get("If-Match")
    if if_match is None:
        raise HTTPException(
            status_code=428, detail="If-Match header required for delete"
        )
    try:
        expected_version = int(if_match)
    except ValueError:
        raise HTTPException(  # noqa: B904
            status_code=400, detail="If-Match must be an integer version"
        )

    db = request.app.state.db_manager.main_db
    if cascade:
        deleted = await cascade_delete_element(
            db, element_id, deleted_by=current_user["id"],
            expected_version=expected_version,
        )
    else:
        deleted = await soft_delete_element(
            db, element_id, deleted_by=current_user["id"],
            expected_version=expected_version,
        )
    if not deleted:
        raise HTTPException(status_code=409, detail="Version conflict or not found")


@router.get("/{element_id}/versions", response_model=list[ElementVersionResponse])
async def get_versions(
    element_id: str,
    request: Request,
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> list[ElementVersionResponse]:
    """Get all versions of an element."""
    db = request.app.state.db_manager.main_db
    versions = await get_element_versions(db, element_id)
    if not versions:
        raise HTTPException(status_code=404, detail="Element not found")
    return [ElementVersionResponse(**v) for v in versions]


@router.get(
    "/{element_id}/versions/{version}",
    response_model=ElementVersionResponse,
)
async def get_version(
    element_id: str,
    version: int,
    request: Request,
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> ElementVersionResponse:
    """Get a specific version of an element."""
    db = request.app.state.db_manager.main_db
    result = await get_element_version(db, element_id, version)
    if result is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return ElementVersionResponse(**result)


@router.get("/{element_id}/diagrams")
async def get_element_diagrams(
    element_id: str,
    request: Request,
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> list[dict[str, str]]:
    """Get diagrams that reference this element."""
    db = request.app.state.db_manager.main_db

    # Check element exists
    element = await get_element(db, element_id)
    if element is None:
        raise HTTPException(status_code=404, detail="Element not found")

    # Find diagrams whose latest version data JSON references this element ID.
    # diagram_versions.data may contain element references in placements or nodes.
    cursor = await db.execute(
        "SELECT DISTINCT d.id, dv.name, d.diagram_type "
        "FROM diagrams d "
        "JOIN diagram_versions dv ON d.id = dv.diagram_id AND d.current_version = dv.version "
        "WHERE d.is_deleted = 0 AND dv.data LIKE ?",
        (f"%{element_id}%",),
    )
    rows = await cursor.fetchall()
    return [
        {"diagram_id": r[0], "name": r[1], "diagram_type": r[2]}
        for r in rows
    ]


@router.get("/{element_id}/stats")
async def get_element_stats(
    element_id: str,
    request: Request,
    _current_user: dict[str, Any] | None = Depends(get_optional_user),  # noqa: B008
) -> dict[str, int]:
    """Get statistics for an element (relationship count, diagram usage count)."""
    db = request.app.state.db_manager.main_db

    # Check element exists
    element = await get_element(db, element_id)
    if element is None:
        raise HTTPException(status_code=404, detail="Element not found")

    # Count relationships where this element is source or target
    rel_cursor = await db.execute(
        "SELECT COUNT(*) FROM relationships "
        "WHERE (source_element_id = ? OR target_element_id = ?) AND is_deleted = 0",
        (element_id, element_id),
    )
    rel_row = await rel_cursor.fetchone()
    relationship_count: int = rel_row[0]

    # Count diagrams referencing this element
    diagram_cursor = await db.execute(
        "SELECT COUNT(DISTINCT d.id) "
        "FROM diagrams d "
        "JOIN diagram_versions dv ON d.id = dv.diagram_id AND d.current_version = dv.version "
        "WHERE d.is_deleted = 0 AND dv.data LIKE ?",
        (f"%{element_id}%",),
    )
    diagram_row = await diagram_cursor.fetchone()
    diagram_usage_count: int = diagram_row[0]

    return {
        "relationship_count": relationship_count,
        "diagram_usage_count": diagram_usage_count,
    }


@router.post("/{element_id}/tags", status_code=201)
async def add_tag(
    element_id: str,
    body: dict[str, Any],
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, str]:
    """Add a tag to an element."""
    db = request.app.state.db_manager.main_db
    tag = body.get("tag", "").strip()
    if not tag or len(tag) > 50:
        raise HTTPException(status_code=400, detail="Tag must be 1-50 characters")
    now = datetime.now(tz=UTC).isoformat()
    try:
        await db.execute(
            "INSERT INTO element_tags (element_id, tag, created_at, created_by) "
            "VALUES (?, ?, ?, ?)",
            (element_id, tag, now, current_user["id"]),
        )
        await db.commit()
    except Exception:
        raise HTTPException(  # noqa: B904
            status_code=409, detail="Tag already exists"
        )
    return {"element_id": element_id, "tag": tag, "created_at": now}


@router.delete("/{element_id}/tags/{tag}")
async def remove_tag(
    element_id: str,
    tag: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, str]:
    """Remove a tag from an element."""
    db = request.app.state.db_manager.main_db
    await db.execute(
        "DELETE FROM element_tags WHERE element_id = ? AND tag = ?",
        (element_id, tag),
    )
    await db.commit()
    return {"status": "ok"}
