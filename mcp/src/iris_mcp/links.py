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
    No-ops when IRIS_WEB_URL is unset or the payload isn't valid JSON.
    """
    base = web_base()
    if not base:
        return payload
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return payload
    decorate_item(data, kind, base)
    return json.dumps(data)


def with_web_urls_list(payload: str, kind: str) -> str:
    """Decorate a JSON-serialised list-of-entities tool response."""
    base = web_base()
    if not base:
        return payload
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return payload
    decorate_list(data, kind, base)
    return json.dumps(data)


def with_web_urls_search(payload: str) -> str:
    """Decorate a JSON-serialised SearchResponse."""
    base = web_base()
    if not base:
        return payload
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return payload
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
