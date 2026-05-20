"""Version API endpoint (v6.17.4).

Reads each Iris component's `pyproject.toml` version field once at
import time and serves the result via `/api/version`. The frontend
`/version` page displays them alongside its own
`frontend/package.json` version.
"""

from __future__ import annotations

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


_BACKEND_VERSION = _read_pyproject_version("backend/pyproject.toml")
_MCP_VERSION = _read_pyproject_version("mcp/pyproject.toml")
_CLI_VERSION = _read_pyproject_version("iris-client/pyproject.toml")


class VersionResponse(BaseModel):
    """Per-component versions of the deployed Iris stack."""

    backend: str | None
    mcp: str | None
    cli: str | None


@router.get("/api/version", response_model=VersionResponse)
async def get_version() -> VersionResponse:
    """Return the deployed version of each Iris Python component.

    Frontend version is known to the SPA itself (from
    `frontend/package.json`) and rendered alongside the backend
    response on the `/version` page.
    """
    return VersionResponse(
        backend=_BACKEND_VERSION,
        mcp=_MCP_VERSION,
        cli=_CLI_VERSION,
    )
