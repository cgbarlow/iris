"""Extension registry API routes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import get_current_user
from app.extensions.models import (
    CheckUpdateResponse,
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
    update_latest_version,
)
from app.extensions.sources import get_source

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

    # v5.5.0 (issue #48): default the source from the registry if the
    # client didn't provide it (most clients won't yet).
    source = get_source(extension_id) or {}
    method = body.source_method or source.get("source_method") or "local"
    source_url = body.source_url or source.get("source_url")

    try:
        result = await install_extension(
            db,
            extension_id=extension_id,
            name=body.name,
            description=body.description,
            version=body.version,
            installed_by=current_user["id"],
            config=body.config,
            source_method=method,
            source_url=source_url,
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


def _compare_semver(a: str, b: str) -> int:
    """Return positive if a > b, negative if a < b, 0 if equal.

    Tolerates prerelease/`v`-prefixes by stripping them first.
    """
    def _parts(v: str) -> list[int]:
        v = v.lstrip("vV")
        out: list[int] = []
        for chunk in v.split("."):
            num = ""
            for c in chunk:
                if c.isdigit():
                    num += c
                else:
                    break
            out.append(int(num) if num else 0)
        return out

    pa, pb = _parts(a), _parts(b)
    while len(pa) < len(pb):
        pa.append(0)
    while len(pb) < len(pa):
        pb.append(0)
    if pa > pb:
        return 1
    if pa < pb:
        return -1
    return 0


@router.post("/{extension_id}/check-update", response_model=CheckUpdateResponse)
async def check_update(
    extension_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> CheckUpdateResponse:
    """v5.5.0 (issue #48): poll the GitHub releases API for the
    extension's source repo, persist the latest tag, and report whether
    an update is available."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    db = request.app.state.db_manager.main_db
    installed = await get_extension(db, extension_id)
    if installed is None:
        raise HTTPException(status_code=404, detail="Extension not found")

    source = get_source(extension_id) or {}
    if source.get("source_method") != "github":
        raise HTTPException(
            status_code=400,
            detail=(
                "check-update is only supported for github-sourced "
                "extensions"
            ),
        )

    owner = source.get("github_owner")
    repo = source.get("github_repo")
    if not owner or not repo:
        raise HTTPException(
            status_code=400,
            detail="Missing github_owner / github_repo in sources.json",
        )

    # GitHub releases API. Optional GITHUB_TOKEN env var raises rate
    # limits but isn't required for public repos.
    import os

    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    latest_tag: str | None = None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:  # noqa: PLR2004
                payload = resp.json()
                # GitHub omits 'v' prefix in `tag_name` only sometimes —
                # the comparator strips it.
                latest_tag = payload.get("tag_name") or payload.get("name")
            elif resp.status_code == 404:  # noqa: PLR2004
                # Repo has no releases yet — leave latest unset and fall
                # through. Not an error; just no upgrade available.
                latest_tag = None
            elif resp.status_code in (403, 429):  # noqa: PLR2004
                # v5.5.7 (issue #55 follow-up): GitHub rate-limits
                # unauthenticated requests at 60/hr per IP. Render's
                # shared egress hits this quickly. Surface a hint at the
                # GITHUB_TOKEN env var rather than a bare status code.
                remaining = resp.headers.get("X-RateLimit-Remaining")
                hint = (
                    "GitHub API rate limit hit. Set GITHUB_TOKEN env var "
                    "on the iris-api service to authenticated requests "
                    "(5000/hr instead of 60/hr)."
                ) if remaining == "0" else (
                    "GitHub API returned 403 (likely missing auth). Set "
                    "GITHUB_TOKEN env var on the iris-api service."
                )
                raise HTTPException(status_code=502, detail=hint)
            else:
                raise HTTPException(
                    status_code=502,
                    detail=f"GitHub API returned {resp.status_code}",
                )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(  # noqa: B904
            status_code=502,
            detail=f"Failed to query GitHub API: {exc}",
        )

    now = datetime.now(tz=UTC).isoformat()
    await update_latest_version(
        db,
        extension_id,
        latest_version=latest_tag,
        checked_at=now,
    )

    update_available = (
        latest_tag is not None
        and _compare_semver(latest_tag, str(installed.get("version") or "0")) > 0
    )

    return CheckUpdateResponse(
        id=extension_id,
        installed_version=str(installed.get("version") or ""),
        latest_version=latest_tag,
        latest_version_checked_at=now,
        update_available=update_available,
        source_url=source.get("source_url"),
    )


@router.post("/{extension_id}/upgrade", response_model=ExtensionResponse)
async def upgrade(
    extension_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> ExtensionResponse:
    """v5.5.0 (issue #48): trigger an automated upgrade. Currently
    supported for mnemos only — pulls the latest from MNEMOSv2 and
    restarts the container."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    db = request.app.state.db_manager.main_db
    installed = await get_extension(db, extension_id)
    if installed is None:
        raise HTTPException(status_code=404, detail="Extension not found")

    source = get_source(extension_id) or {}
    if not source.get("supports_auto_upgrade"):
        raise HTTPException(
            status_code=501,
            detail=(
                f"Automated upgrade not supported for '{extension_id}' yet."
            ),
        )

    if extension_id == "mnemos":
        from app.mnemos.setup import (  # noqa: PLC0415
            clone_or_update_repo,
            start_container,
            stop_container,
        )

        ok, msg = await stop_container()
        if not ok:
            print(f"[MNEMOS] Warning during upgrade stop: {msg}", flush=True)

        cloned, clone_msg = clone_or_update_repo(
            source_url=source.get("source_url"),
        )
        if not cloned:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update mnemos repo: {clone_msg}",
            )

        ok, msg = await start_container()
        if not ok:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to restart mnemos: {msg}",
            )

        # The new installed_version is the latest_version we found.
        if installed.get("latest_version"):
            now = datetime.now(tz=UTC).isoformat()
            await db.execute(
                "UPDATE extensions SET version = ?, updated_at = ? WHERE id = ?",
                (installed["latest_version"], now, extension_id),
            )
            await db.commit()

    refreshed = await get_extension(db, extension_id)
    if refreshed is None:
        raise HTTPException(status_code=500, detail="Extension vanished")
    return ExtensionResponse(**refreshed)
