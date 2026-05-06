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
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger("app.extensions.sources")

# repo-root/extensions/sources.json — three levels up from this module.
_SOURCES_PATH = Path(__file__).resolve().parents[3] / "extensions" / "sources.json"

# v5.5.6 (issue #55 root cause): fail loud if the registry file isn't
# found at runtime. Pre-fix the Dockerfile only copied backend/ +
# iris-client/ + mcp/, missing extensions/ — so _load() returned {}
# and the check-update endpoint reported every extension as
# 'not github-sourced'. The Dockerfile now COPYs extensions/ too;
# this warning surfaces any regression of that copy.
_LOAD_WARNED = False


def _load() -> dict[str, dict[str, Any]]:
    global _LOAD_WARNED
    if not _SOURCES_PATH.is_file():
        if not _LOAD_WARNED:
            log.warning(
                "extensions registry not found at %s — check-update will report "
                "every extension as non-github. Verify the deploy includes the "
                "extensions/ directory at the repo root.",
                _SOURCES_PATH,
            )
            _LOAD_WARNED = True
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
