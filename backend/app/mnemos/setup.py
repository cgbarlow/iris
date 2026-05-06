"""MNEMOS extension setup — container lifecycle and SDK wiring (ADR-111).

Handles starting/stopping the MNEMOS Docker container and making the
mnemos_sdk importable when the extension is installed.

v5.5.0 (issue #48): added clone_or_update_repo() so the upgrade
endpoint can pull from MNEMOSv2 (the new fork at
https://github.com/ro0TuX777/MNEMOSv2) without an operator manually
re-cloning. Default source URL is configurable via IRIS_MNEMOS_REPO_URL.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys

log = logging.getLogger("app.mnemos.setup")

# Path to the cloned MNEMOS repository
_MNEMOS_REPO = os.environ.get(
    "IRIS_MNEMOS_REPO_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "MNEMOS"),
)
_MNEMOS_REPO = os.path.abspath(_MNEMOS_REPO)

# v5.5.0 (issue #48): default source URL for fresh clones / upgrades.
# Override at deploy time via IRIS_MNEMOS_REPO_URL.
_DEFAULT_MNEMOS_REPO_URL = "https://github.com/ro0TuX777/MNEMOSv2.git"


def _mnemos_repo_exists() -> bool:
    """Check if the MNEMOS repo is available on disk."""
    return os.path.isdir(_MNEMOS_REPO) and os.path.isfile(
        os.path.join(_MNEMOS_REPO, "docker-compose.yml")
    )


def clone_or_update_repo(
    *,
    source_url: str | None = None,
    branch: str | None = None,
) -> tuple[bool, str]:
    """Ensure the MNEMOS repo at _MNEMOS_REPO is up to date.

    If the directory doesn't exist, clones source_url. If it exists and
    is a git repo, runs `git fetch && git reset --hard origin/<branch>`
    to bring it to the latest. Returns (success, message).

    Used by the v5.5.0 upgrade endpoint and by start_container() on
    fresh installs.
    """
    url = source_url or os.environ.get("IRIS_MNEMOS_REPO_URL") or _DEFAULT_MNEMOS_REPO_URL
    target_branch = branch or os.environ.get("IRIS_MNEMOS_REPO_BRANCH") or "main"

    if not os.path.isdir(_MNEMOS_REPO):
        # Fresh clone.
        parent = os.path.dirname(_MNEMOS_REPO)
        try:
            os.makedirs(parent, exist_ok=True)
            proc = subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", target_branch, url, _MNEMOS_REPO],
                capture_output=True, check=False, timeout=120,
            )
            if proc.returncode != 0:
                err = proc.stderr.decode().strip() or proc.stdout.decode().strip()
                return False, f"git clone failed: {err}"
            return True, f"Cloned {url}@{target_branch}"
        except Exception as exc:  # noqa: BLE001
            return False, f"git clone failed: {exc}"

    # Existing checkout — update.
    if not os.path.isdir(os.path.join(_MNEMOS_REPO, ".git")):
        return False, f"{_MNEMOS_REPO} exists but isn't a git repo; refusing to overwrite"

    try:
        subprocess.run(
            ["git", "fetch", "--depth", "1", "origin", target_branch],
            cwd=_MNEMOS_REPO, capture_output=True, check=True, timeout=60,
        )
        subprocess.run(
            ["git", "reset", "--hard", f"origin/{target_branch}"],
            cwd=_MNEMOS_REPO, capture_output=True, check=True, timeout=30,
        )
        return True, f"Pulled origin/{target_branch}"
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or b"").decode().strip()
        return False, f"git update failed: {err}"
    except Exception as exc:  # noqa: BLE001
        return False, f"git update failed: {exc}"


def ensure_sdk_importable() -> None:
    """Add the MNEMOS repo to sys.path and ensure its dependencies are available."""
    if _mnemos_repo_exists() and _MNEMOS_REPO not in sys.path:
        sys.path.insert(0, _MNEMOS_REPO)
        print(f"[MNEMOS] Added {_MNEMOS_REPO} to Python path", flush=True)

    # mnemos_sdk depends on `requests` — install if missing
    try:
        import requests  # noqa: F401
    except ImportError:
        print("[MNEMOS] Installing requests (mnemos_sdk dependency)...", flush=True)
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "requests"],
            capture_output=True, check=False,
        )


async def start_container() -> tuple[bool, str]:
    """Build and start the MNEMOS Docker container.

    Returns (success, message).
    """
    if not _mnemos_repo_exists():
        return False, f"MNEMOS repo not found at {_MNEMOS_REPO}"

    print(f"[MNEMOS] Starting container from {_MNEMOS_REPO}...", flush=True)

    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "compose", "up", "-d", "--build",
            cwd=_MNEMOS_REPO,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

        if proc.returncode != 0:
            err = stderr.decode().strip() or stdout.decode().strip()
            print(f"[MNEMOS] Container start failed: {err}", flush=True)
            return False, f"docker compose failed: {err}"

        print("[MNEMOS] Container started, waiting for health...", flush=True)

        # Poll health endpoint
        import httpx

        for _ in range(30):  # 30 attempts × 2s = 60s max
            await asyncio.sleep(2)
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.get("http://localhost:8700/health")
                    if resp.status_code == 200:  # noqa: PLR2004
                        print("[MNEMOS] Container healthy and ready", flush=True)
                        return True, "MNEMOS container started and healthy"
            except Exception:  # noqa: BLE001
                pass

        print("[MNEMOS] Container started but health check timed out", flush=True)
        return True, "Container started but health check timed out (may still be loading models)"

    except asyncio.TimeoutError:
        return False, "docker compose timed out after 120s"
    except Exception as exc:  # noqa: BLE001
        return False, f"Failed to start container: {exc}"


async def stop_container() -> tuple[bool, str]:
    """Stop and remove the MNEMOS Docker container.

    Returns (success, message).
    """
    if not _mnemos_repo_exists():
        return True, "MNEMOS repo not found, nothing to stop"

    print("[MNEMOS] Stopping container...", flush=True)

    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "compose", "down",
            cwd=_MNEMOS_REPO,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        if proc.returncode != 0:
            err = stderr.decode().strip()
            print(f"[MNEMOS] Container stop failed: {err}", flush=True)
            return False, f"docker compose down failed: {err}"

        print("[MNEMOS] Container stopped", flush=True)
        return True, "MNEMOS container stopped"

    except asyncio.TimeoutError:
        return False, "docker compose down timed out"
    except Exception as exc:  # noqa: BLE001
        return False, f"Failed to stop container: {exc}"
