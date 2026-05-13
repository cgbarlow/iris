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


# v6.0.6 (ADR-167): orient wrapper marker. Used both as the prefix the
# wrapper produces AND as the idempotency check ("starts with this →
# already wrapped, don't re-wrap"). Keep these in sync.
_ORIENT_MARKER = "[ORIENT — DO THESE STEPS BEFORE RESPONDING TO THE USER]"


def _orient_wrapper(kind: str, entity_id: str) -> str:
    """Build the imperative orient prefix for a single scope.

    v6.0.6 (ADR-167): claude.ai's hosted MCP integration does not
    reliably surface `InitializeResult.instructions` to the model —
    verified post-v6.0.5 when the strong canonical body was confirmed
    on the wire but the model still skipped the structural-overview
    call. The orient-first directive is therefore re-embedded into the
    tool RESPONSE itself, prepended to any non-empty `mcp_system_context`
    field. The model has been consistently shown to read tool-response
    bodies; this puts the directive where it definitely lands.

    The wrapper pre-fills the scope's id (`set_id="..."` /
    `collection_id="..."`) so the model has the exact tool-call
    signature in hand — no inference needed.
    """
    if kind == "set":
        id_kw = f'set_id="{entity_id}"'
    elif kind == "collection":
        id_kw = f'collection_id="{entity_id}"'
    else:
        id_kw = f'id="{entity_id}"'
    return (
        f"{_ORIENT_MARKER}\n"
        f"This scope is a {kind} ({id_kw}). The orient sheet below names a "
        f"structural-overview call AND a numbered menu. Before responding "
        f"to the user, you MUST, in order:\n"
        f"\n"
        f"  1. Briefly describe the scope (one sentence based on its name "
        f"and description).\n"
        f"\n"
        f"  2. INVOKE the structural-overview call named below, passing "
        f"this scope's {id_kw}. The TOC is mandatory, not optional. If the "
        f"named tool is not currently in your toolset, request a tool-load "
        f"first — do NOT skip this step.\n"
        f"     FORMAT: render the result as a markdown bullet list, ONE "
        f"ENTRY PER LINE, with each entry as a clickable markdown link "
        f"using the node's `web_url` field as the target. Example: \n"
        f"       - [Part A — DoView Planning Fundamentals (5 chapters)]"
        f"(https://iris-uat.chrisbarlow.nz/packages/abc...)\n"
        f"       - [Part B — DoView Drawing and Strategy Principles "
        f"(25 chapters)](https://iris-uat.chrisbarlow.nz/packages/def...)\n"
        f"     Show the URL as the link target only — do NOT also print "
        f"the bare URL alongside. Each node has `name`, `web_url`, and "
        f"`children` fields; the chapter count is `len(children)`.\n"
        f"\n"
        f"  3. Offer the menu options below to the user. The options "
        f"are LITERAL TEXT — copy each one CHARACTER-BY-CHARACTER from the "
        f"orient sheet's MENU section into your response. Do NOT summarise. "
        f"Do NOT shorten. Do NOT drop parenthetical examples like "
        f"\"(e.g. J06 — Mathematization of Outcomes Theory)\". Long options "
        f"are intentional.\n"
        f"\n"
        f"FULFILLING THE MENU OPTIONS — YOU do the work, not a separate AI:\n"
        f"\n"
        f"  - Cross-package, cross-set, or cross-collection questions are "
        f"answered by YOUR reasoning over data you read via the read-only "
        f"MCP tools (search, get_diagram, get_element, get_package, get_set, "
        f"get_collection, list_*, package_hierarchy). There is no \"ask Iris "
        f"AI\" tool — it has been removed (v6.0.8). Walk the data yourself.\n"
        f"\n"
        f"  - DoView outcomes-theory analyses and visual outcomes_map "
        f"diagrams are drafted by YOU using your own reasoning, following "
        f"the creation cascade from `get_response_prompt(purpose='creation_"
        f"format', notation=..., diagram_type=...)`. Persist the result by "
        f"calling `create_diagram` (single) or `apply_diagram_creation` "
        f"(batch). Do NOT look for a separate AI-analysis tool — none exists.\n"
        f"\n"
        f"Do NOT ask \"want me to load the table of contents?\" — load it "
        f"yourself. Do NOT respond with just the menu and skip the TOC. "
        f"Do NOT respond with just the TOC and skip the menu.\n"
        f"\n"
        f"---\n"
        f"\n"
    )


def wrap_orient(item: Any, kind: str) -> None:  # noqa: ANN401
    """In-place: prepend the orient directive to `item["mcp_system_context"]`
    when the field is set on a scope (set or collection).

    No-op when:
    - `item` isn't a dict.
    - The field is missing, None, empty, or whitespace-only.
    - The entity has no resolvable `id` (we'd produce an incomplete
      tool-call signature otherwise).
    - The field already starts with the orient marker (idempotent —
      reprocessing the same payload doesn't double-wrap).
    - `kind` is anything other than "set" or "collection". Other entity
      kinds don't carry scope-orient semantics; even if a rogue server
      set the field on a diagram, we leave it alone.
    """
    if not isinstance(item, dict):
        return
    if kind not in ("set", "collection"):
        return
    ctx = item.get("mcp_system_context")
    if not isinstance(ctx, str) or not ctx.strip():
        return
    if ctx.startswith(_ORIENT_MARKER):
        return
    entity_id = item.get("id")
    if not isinstance(entity_id, str) or not entity_id:
        return
    item["mcp_system_context"] = _orient_wrapper(kind, entity_id) + ctx


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


def decorate_tree(
    nodes: list[Any], kind: str, base: str | None = None,
) -> None:
    """v6.0.7: in-place recursive web_url decoration for tree-shaped
    responses (e.g. `package_hierarchy`).

    `decorate_list` only walks the top level; package_hierarchy returns
    nested `children` arrays that also need web_urls so the model can
    render each Part / chapter as a clickable markdown link. Same kind
    applies at every depth — package_hierarchy is homogeneously packages
    all the way down.
    """
    if not isinstance(nodes, list):
        return
    resolved_base = base if base is not None else web_base()
    if not resolved_base:
        return
    for node in nodes:
        decorate_item(node, kind, resolved_base)
        if isinstance(node, dict):
            children = node.get("children")
            if isinstance(children, list):
                decorate_tree(children, kind, resolved_base)


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
    whether IRIS_WEB_URL is configured. v6.0.6 (ADR-167) additionally
    prepends the orient directive to `mcp_system_context` on set /
    collection responses, regardless of IRIS_WEB_URL. No-ops on
    invalid JSON.
    """
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return payload
    _strip_sensitive_keys(data)
    wrap_orient(data, kind)
    base = web_base()
    if base:
        decorate_item(data, kind, base)
    return json.dumps(data)


def with_web_urls_list(payload: str, kind: str) -> str:
    """Decorate a JSON-serialised list-of-entities tool response.

    Also strips MCP-sensitive keys from each item (v5.8.2, ADR-151)
    regardless of whether IRIS_WEB_URL is configured. v6.0.6 (ADR-167)
    additionally prepends the orient directive to every set / collection
    item's `mcp_system_context` field.
    """
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return payload
    _strip_sensitive_keys_list(data)
    if isinstance(data, list):
        for item in data:
            wrap_orient(item, kind)
    base = web_base()
    if base:
        decorate_list(data, kind, base)
    return json.dumps(data)


def with_web_urls_search(payload: str) -> str:
    """Decorate a JSON-serialised SearchResponse.

    Also strips MCP-sensitive keys from each result (v5.8.2, ADR-151)
    regardless of whether IRIS_WEB_URL is configured. v6.0.6 (ADR-167)
    additionally prepends the orient directive to set / collection
    results that carry a non-empty `mcp_system_context` — pre-filling
    the scope's id in the tool-call signature so the model has the
    exact `package_hierarchy(set_id="...")` call in hand.
    """
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return payload
    if isinstance(data, dict):
        results = data.get("results")
        if isinstance(results, list):
            _strip_sensitive_keys_list(results)
            for r in results:
                if isinstance(r, dict):
                    kind = r.get("result_type")
                    if isinstance(kind, str):
                        wrap_orient(r, kind)
    base = web_base()
    if base:
        decorate_search(data, base)
    return json.dumps(data)


__all__ = [
    "decorate_item",
    "decorate_list",
    "decorate_search",
    "decorate_tree",
    "web_base",
    "web_url_for",
    "with_web_url",
    "with_web_urls_list",
    "with_web_urls_search",
    "with_web_urls_tree",
    "wrap_orient",
]


def with_web_urls_tree(payload: str, kind: str) -> str:
    """v6.0.7: decorate a JSON-serialised tree response (e.g.
    `package_hierarchy`) recursively, so every node at every depth
    carries a `web_url`. Strips sensitive keys at the top level only
    (children inherit the homogeneous kind, no per-level scrub needed
    for the current schema). No-ops on invalid JSON.
    """
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return payload
    if isinstance(data, list):
        _strip_sensitive_keys_list(data)
    base = web_base()
    if base:
        decorate_tree(data, kind, base)
    return json.dumps(data)
