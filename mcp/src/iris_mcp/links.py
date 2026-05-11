"""v5.6.1: web-UI link decoration for tool responses.

The MCP host's LLM otherwise has to *guess* the iris web URL when asked
to cite a diagram or element — e.g. "https://iris-uat.chrisbarlow.nz/views/<id>"
— which has produced broken links when the guess was wrong.

We solve this by decorating every entity dict the tools return with a
`web_url` field. The LLM sees the resolved URL in the response and can
quote it verbatim. When `IRIS_WEB_URL` isn't configured (local dev),
decoration is a no-op and responses are identical to before.
"""

from __future__ import annotations

import json
import os
from typing import Any

# Map an entity "kind" → the frontend path segment that displays it.
# The keys cover both singular and plural so search results
# (`result_type: "diagram"`) and list endpoints (kind="diagrams") all
# resolve through the same table.
_KIND_TO_PATH: dict[str, str] = {
    "diagram": "views",
    "diagrams": "views",
    "element": "elements",
    "elements": "elements",
    "package": "packages",
    "packages": "packages",
    "set": "sets",
    "sets": "sets",
    "collection": "collections",
    "collections": "collections",
}


def web_base() -> str | None:
    """Read IRIS_WEB_URL fresh each call so tests can monkeypatch the env."""
    raw = os.environ.get("IRIS_WEB_URL")
    return raw.rstrip("/") if raw else None


# v5.8.2 (ADR-151): keys that must never leave the MCP boundary as tool
# data. Currently just `system_prompt` — scope prompts get surfaced to
# clients via the MCP `prompts` capability instead (ADR-152, v5.8.3).
_STRIPPED_KEYS: tuple[str, ...] = ("system_prompt",)


def _strip_sensitive_keys(item: Any) -> None:
    """In-place: remove any sensitive keys from a single entity dict."""
    if not isinstance(item, dict):
        return
    for key in _STRIPPED_KEYS:
        item.pop(key, None)


def _strip_sensitive_keys_list(items: Any) -> None:
    """In-place: apply `_strip_sensitive_keys` to every dict in a list."""
    if not isinstance(items, list):
        return
    for item in items:
        _strip_sensitive_keys(item)


def web_url_for(kind: str, entity_id: str, base: str | None = None) -> str | None:
    """Build a `<base>/<path>/<id>` URL for the given entity, or None if
    the web base or kind is unknown."""
    resolved_base = base if base is not None else web_base()
    if not resolved_base or not entity_id:
        return None
    path = _KIND_TO_PATH.get(kind)
    if not path:
        return None
    return f"{resolved_base}/{path}/{entity_id}"


def decorate_item(item: dict[str, Any], kind: str, base: str | None = None) -> None:
    """In-place: attach `web_url` to a single entity dict if we can."""
    if not isinstance(item, dict):
        return
    entity_id = item.get("id")
    if not isinstance(entity_id, str):
        return
    url = web_url_for(kind, entity_id, base)
    if url:
        item.setdefault("web_url", url)


def decorate_list(items: list[Any], kind: str, base: str | None = None) -> None:
    """In-place: attach web_urls to every dict-shaped item in a homogeneous list."""
    if not isinstance(items, list):
        return
    resolved_base = base if base is not None else web_base()
    if not resolved_base:
        return
    for item in items:
        decorate_item(item, kind, resolved_base)


def decorate_search(payload: dict[str, Any], base: str | None = None) -> None:
    """In-place: attach web_urls to a SearchResponse dict — each result
    carries a `result_type` discriminator (diagram | element | …)."""
    if not isinstance(payload, dict):
        return
    resolved_base = base if base is not None else web_base()
    if not resolved_base:
        return
    results = payload.get("results")
    if not isinstance(results, list):
        return
    for r in results:
        if not isinstance(r, dict):
            continue
        kind = r.get("result_type")
        if isinstance(kind, str):
            decorate_item(r, kind, resolved_base)


# ----- public helpers used by tool handlers -----------------------------------


def with_web_url(payload: str, kind: str) -> str:
    """Decorate a JSON-serialised single-entity tool response.

    `kind` is the kind we expect (e.g. "diagram" for `get_diagram`).
    Also strips MCP-sensitive keys (v5.8.2, ADR-151) regardless of
    whether IRIS_WEB_URL is configured. No-ops on invalid JSON.
    """
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return payload
    _strip_sensitive_keys(data)
    base = web_base()
    if base:
        decorate_item(data, kind, base)
    return json.dumps(data)


def with_web_urls_list(payload: str, kind: str) -> str:
    """Decorate a JSON-serialised list-of-entities tool response.

    Also strips MCP-sensitive keys from each item (v5.8.2, ADR-151)
    regardless of whether IRIS_WEB_URL is configured.
    """
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return payload
    _strip_sensitive_keys_list(data)
    base = web_base()
    if base:
        decorate_list(data, kind, base)
    return json.dumps(data)


def with_web_urls_search(payload: str) -> str:
    """Decorate a JSON-serialised SearchResponse.

    Also strips MCP-sensitive keys from each result (v5.8.2, ADR-151)
    regardless of whether IRIS_WEB_URL is configured.
    """
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return payload
    if isinstance(data, dict):
        results = data.get("results")
        if isinstance(results, list):
            _strip_sensitive_keys_list(results)
    base = web_base()
    if base:
        decorate_search(data, base)
    return json.dumps(data)


__all__ = [
    "decorate_item",
    "decorate_list",
    "decorate_search",
    "web_base",
    "web_url_for",
    "with_web_url",
    "with_web_urls_list",
    "with_web_urls_search",
]
