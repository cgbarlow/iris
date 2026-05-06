"""v5.5.0 (issue #48): shared extension source registry.

Reads `extensions/sources.json` at the repo root. The same file is also
read by `scripts/check_extension_updates.py` (the daily GitHub Action),
so the source URLs / GitHub owner+repo coordinates / auto-upgrade
flags are defined once.

The router uses this on install to populate `source_method` and
`source_url`; the check-update endpoint uses it to find the GitHub
repo to query for the latest release.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# repo-root/extensions/sources.json — three levels up from this module.
_SOURCES_PATH = Path(__file__).resolve().parents[3] / "extensions" / "sources.json"


def _load() -> dict[str, dict[str, Any]]:
    if not _SOURCES_PATH.is_file():
        return {}
    with _SOURCES_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    return data.get("extensions", {})


def get_known_sources() -> dict[str, dict[str, Any]]:
    """Return { extension_id: { name, description, source_method, source_url, github_owner?, github_repo?, supports_auto_upgrade } }."""
    return _load()


def get_source(extension_id: str) -> dict[str, Any] | None:
    """Return the source metadata for one extension, or None."""
    return _load().get(extension_id)
