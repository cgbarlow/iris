"""Version API endpoint (v6.17.4+).

Reads each Iris component's `pyproject.toml` version field once at
import time and serves the result via `/api/version`. Also exposes
the build's git commit sha (from the ``IRIS_GIT_SHA`` /
``RENDER_GIT_COMMIT`` env vars, with a ``git rev-parse HEAD``
fallback for local dev).

v6.17.5 convention: bump backend / mcp / iris-client pyproject
versions in lockstep with ``frontend/package.json`` on every Iris
release so the four numbers always agree on the deployed version.
"""

from __future__ import annotations

import os
import subprocess
import tomllib
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["version"])

# `backend/app/version_router.py` → `<repo>/backend/app` → up two = repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _read_pyproject_version(rel: str) -> str | None:
    path = _REPO_ROOT / rel
    if not path.exists():
        return None
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
        project = data.get("project") or {}
        ver = project.get("version")
        return str(ver) if ver else None
    except (OSError, tomllib.TOMLDecodeError):
        return None


def _resolve_git_sha() -> str | None:
    """Best-effort lookup of the build's git sha."""
    for env in ("IRIS_GIT_SHA", "RENDER_GIT_COMMIT"):
        v = os.environ.get(env)
        if v:
            return v[:40]
    try:
        out = subprocess.check_output(  # noqa: S603, S607
            ["git", "rev-parse", "HEAD"],
            cwd=_REPO_ROOT,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        sha = out.decode("ascii", errors="ignore").strip()
        return sha or None
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None


_BACKEND_VERSION = _read_pyproject_version("backend/pyproject.toml")
_MCP_VERSION = _read_pyproject_version("mcp/pyproject.toml")
_CLI_VERSION = _read_pyproject_version("iris-client/pyproject.toml")
_GIT_SHA = _resolve_git_sha()


class VersionResponse(BaseModel):
    """Per-component versions of the deployed Iris stack."""

    backend: str | None
    mcp: str | None
    cli: str | None
    git_sha: str | None = None


@router.get("/api/version", response_model=VersionResponse)
async def get_version() -> VersionResponse:
    """Return the deployed version of each Iris Python component plus
    the build's git commit sha. Frontend version is known to the SPA
    itself (from `frontend/package.json`) and rendered alongside the
    backend response on the `/version` page."""
    return VersionResponse(
        backend=_BACKEND_VERSION,
        mcp=_MCP_VERSION,
        cli=_CLI_VERSION,
        git_sha=_GIT_SHA,
    )
