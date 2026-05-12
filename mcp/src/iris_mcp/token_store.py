"""On-disk credential store for iris-mcp (ADR-160, SPEC-160-A).

A small key-value store under `~/.iris-mcp/`. Each authenticated Iris
URL gets its own JSON file (`<sha256(iris_url)[:16]>.json`, mode 0600)
so a single iris-mcp install can hold credentials for multiple Iris
deployments (e.g. local dev + UAT + prod) without collisions.

File contents::

    {
      "iris_url": "https://iris-uat.chrisbarlow.nz",
      "token": "iris_pat_abcdef12_...",
      "expires_at": "2026-08-10T14:32:11+00:00"
    }

`expires_at` is the wall-clock UTC ISO-8601 string from the backend;
`None` means "backend-managed" (PAT-paste path: backend owns expiry).
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DIRNAME = ".iris-mcp"


def _dir() -> Path:
    return Path.home() / DIRNAME


def token_file_path(iris_url: str) -> Path:
    """Return the per-Iris-URL token file path under `~/.iris-mcp/`."""
    digest = hashlib.sha256(iris_url.encode("utf-8")).hexdigest()[:16]
    return _dir() / f"{digest}.json"


def _is_expired(expires_at: str | None) -> bool:
    if expires_at is None:
        return False
    try:
        when = datetime.fromisoformat(expires_at)
    except ValueError:
        return True
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return when <= datetime.now(tz=UTC)


def load_token(iris_url: str) -> str | None:
    """Return the persisted PAT for `iris_url`, or None if missing/expired/corrupt."""
    path = token_file_path(iris_url)
    if not path.exists():
        return None
    try:
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    token = payload.get("token")
    if not isinstance(token, str) or not token:
        return None
    if _is_expired(payload.get("expires_at")):
        return None
    return token


def save_token(
    iris_url: str,
    token: str,
    expires_at: str | None,
) -> Path:
    """Persist `token` for `iris_url`. Returns the file path.

    Sets directory mode 0700 and file mode 0600. Overwrites any
    existing token for the same URL.
    """
    directory = _dir()
    directory.mkdir(mode=0o700, exist_ok=True)
    try:
        os.chmod(directory, 0o700)  # noqa: PTH101 — chmod is fine on Path's parent
    except OSError:
        pass
    path = token_file_path(iris_url)
    payload: dict[str, Any] = {
        "iris_url": iris_url,
        "token": token,
        "expires_at": expires_at,
    }
    serialised = json.dumps(payload, indent=2, sort_keys=True)
    path.write_text(serialised, encoding="utf-8")
    try:
        os.chmod(path, 0o600)  # noqa: PTH101
    except OSError:
        pass
    return path
