"""Tool definitions for iris-mcp (SPEC-131-A).

Each entry pairs an LLM-facing description with an async handler that
calls the shared `IrisClient`. Keeping all tools in a single module means
adding/removing a capability is a one-line diff.
"""

from __future__ import annotations

import json
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from iris_client import IrisClient
from iris_client.exceptions import IrisAuthError, IrisHTTPError
from mcp import types

from iris_mcp.errors import format_error
from iris_mcp.links import (
    with_web_url,
    with_web_urls_list,
    with_web_urls_search,
    with_web_urls_tree,
)
def _resource_metadata_url() -> str:
    """Return the iris-mcp Protected Resource metadata URL.

    Prefers `IRIS_MCP_PUBLIC_URL` (operator-set) over `IRIS_WEB_URL`
    over `IRIS_URL`.
    """
    base = (
        os.environ.get("IRIS_MCP_PUBLIC_URL")
        or os.environ.get("IRIS_WEB_URL")
        or os.environ.get("IRIS_URL", "http://localhost:8000")
    )
    return base.rstrip("/") + "/.well-known/oauth-protected-resource"


def _auth_required_payload(action: str) -> str:
    """ADR-164 / ADR-169: shared OAuth-setup-guidance payload.

    Every write tool returns this exact shape when iris-mcp gets a 401
    from the backend, so the model can guide the user uniformly.

    The OAuth handshake is fully automatic in MCP — the client (e.g.
    claude.ai) reads the RFC 9728 Protected Resource metadata at
    `/.well-known/oauth-protected-resource`, performs RFC 7591 Dynamic
    Client Registration with the Authorization Server, and pops a
    browser window for the user to sign in. There is **no manual
    client_id/secret entry** on the user's side. If the user is seeing
    this message instead of an automatic sign-in popup, the client
    hasn't initiated the OAuth flow yet — usually a one-click "Connect"
    button in the client's connector UI triggers it.
    """
    return json.dumps({
        "success": False,
        "error": "auth_required",
        "message": (
            f"{action} requires that you (the user) sign in to Iris.\n\n"
            "Tell the user: in your MCP client's connector list, find "
            "the Iris connector and click \"Connect\" / \"Sign in\" "
            "(in claude.ai: Settings → Connectors → Iris). A browser "
            "tab will open for you to sign in to Iris and approve "
            "access. You will NOT be asked for a client_id or secret "
            "— the MCP client registers itself automatically via "
            "Dynamic Client Registration (RFC 7591).\n\n"
            "If no sign-in button appears, try removing and re-adding "
            "the connector to force re-discovery of the OAuth metadata.\n\n"
            "Do NOT call any auth-related tool yourself — the OAuth "
            "handshake is between the MCP client and Iris, not via "
            "tool calls. Read tools (search, get_*, list_*, "
            "package_hierarchy) work without sign-in; only writes "
            "(create_*, update_*) need it."
        ),
        "next_step": "user_signs_in_via_mcp_client_connector_ui",
        "oauth_resource_metadata_url": _resource_metadata_url(),
    })


_DESTINATION_PREAMBLE = """
BEFORE CALLING, confirm with the user where they want this saved.

Options to offer the user (use AskUserQuestion when the client
supports it; otherwise a numbered list):

  1. An existing set (or set + parent package) the user names.
     Use list_collections / list_sets / package_hierarchy to
     resolve human names to ids.
  2. A new set in an existing collection.
     Call create_set(name=..., collection_id=<existing>) first,
     then save against the returned set.id.
  3. A new collection and a new set.
     Call create_collection(name=...) then
     create_set(name=..., collection_id=<new>), then save.
  4. (Optional) Also nest under a new package.
     Call create_package(name=..., set_id=<chosen>) and pass its
     id as parent_package_id.

Only call this save tool once the user has chosen / confirmed a
destination. Do not pick a destination silently.
""".strip()


_CREATION_FLOW_PREAMBLE = """
Generic save for a new diagram of any (notation, diagram_type) pair.

CREATION FLOW (recommended):
  1. Discover: call list_notations / list_diagram_types if you don't
     already know which (notation, diagram_type) the user wants.
  2. Fetch the creation guidance: get_response_prompt(notation=...,
     diagram_type=..., purpose='creation_format'). The body carries
     the layered creation cascade (base + notation + diagram_type)
     used by Iris AI when generating diagrams. For DoView it includes
     the Stage 0 setup questions (Q1..Q6), the entity types, the
     colour palette, and the outcomes_map layout rules.
  2a. CRITICAL for content-bearing markdown diagrams
      (notation='markdown', e.g. diagram_type='doview_analysis'):
      ALSO fetch get_response_prompt(notation='markdown',
      diagram_type=..., purpose='response_format'). The response_format
      rules govern the OUTPUT STRUCTURE of the markdown body
      (required opening sentence, section headings, citation format,
      framing language). Apply BOTH cascades to the content you
      generate. Without this fetch, the markdown body will not
      follow the structure rules and the diagram will fail
      content-compliance review.
  3. Run the guided conversation IN CHAT with the user. Use
     AskUserQuestion when supported; numbered list otherwise.
  4. Compose the `data` JSON locally per the creation prompt's rules.
     For visual diagrams (notation in doview / archimate / c4 / uml /
     simple / bpmn), data is a Svelte-Flow-shaped {nodes, edges}
     payload. For markdown diagrams, data is {"content": "<markdown>"}
     and the <markdown> must follow the response_format rules from
     step 2a.
  5. Confirm destination with the user (see destination preamble
     below).
  6. Call create_diagram with the composed data.
""".strip()


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[IrisClient, dict[str, Any]], Awaitable[str | bytes]]


def _str_arg(name: str, description: str, *, required: bool = True) -> tuple[dict, bool]:
    return ({"type": "string", "description": description}, required)


def _schema(props: dict[str, tuple[dict, bool]]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {k: v for k, (v, _) in props.items()},
        "required": [k for k, (_, req) in props.items() if req],
    }


async def _search(c: IrisClient, args: dict[str, Any]) -> str:
    result = await c.search(
        args["query"],
        set_id=args.get("set_id"),
        collection_id=args.get("collection_id"),
        limit=int(args.get("limit", 25)),
    )
    return with_web_urls_search(result.model_dump_json())


async def _get_diagram(c: IrisClient, args: dict[str, Any]) -> str:
    return with_web_url(
        (await c.get_diagram(args["diagram_id"])).model_dump_json(), "diagram",
    )


async def _list_diagrams(c: IrisClient, args: dict[str, Any]) -> str:
    """v6.6.4: accepts page/page_size/parent_package_id so a model can
    walk big sets without missing root-level diagrams that paginate
    off page 1 under the backend's default ``updated_at DESC``
    ordering. Mirrors the `list_packages` wiring (ADR-158)."""
    rows = await c.list_diagrams(
        set_id=args.get("set_id"),
        parent_package_id=args.get("parent_package_id"),
        page=args.get("page", 1),
        page_size=args.get("page_size", 50),
    )
    return with_web_urls_list(json.dumps([r.model_dump() for r in rows]), "diagram")


async def _get_element(c: IrisClient, args: dict[str, Any]) -> str:
    return with_web_url(
        (await c.get_element(args["element_id"])).model_dump_json(), "element",
    )


async def _list_elements(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-184 (v6.7.0): adds ``package_id`` three-valued filter.

    Bypasses the typed client to forward ``package_id="null"`` verbatim
    (the iris-client typed method doesn't yet support the sentinel).
    """
    params: dict[str, Any] = {}
    if args.get("set_id"):
        params["set_id"] = args["set_id"]
    if "package_id" in args and args["package_id"] is not None:
        params["package_id"] = args["package_id"]
    resp = await c._request("GET", "/api/elements", params=params)
    items = resp.json().get("items", [])
    return with_web_urls_list(json.dumps(items), "element")


async def _get_package(c: IrisClient, args: dict[str, Any]) -> str:
    return with_web_url(
        (await c.get_package(args["package_id"])).model_dump_json(), "package",
    )


async def _list_packages(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-158 (v5.13.0): accepts page/page_size/parent_package_id so
    a model can walk big sets without missing chapters that paginate
    onto page 2+."""
    rows = await c.list_packages(
        set_id=args.get("set_id"),
        collection_id=args.get("collection_id"),
        parent_package_id=args.get("parent_package_id"),
        page=args.get("page", 1),
        page_size=args.get("page_size", 50),
    )
    return with_web_urls_list(json.dumps([r.model_dump() for r in rows]), "package")


async def _package_hierarchy(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-158 (v5.13.0): return the complete package tree in one call.
    Prefer this over `list_packages` for structural overview.

    v6.0.7: each node (and every child recursively) is decorated with
    `web_url` via `with_web_urls_tree` so the model can render each
    Part / chapter as a clickable markdown link.
    """
    nodes = await c.package_hierarchy(
        set_id=args.get("set_id"),
        root_id=args.get("root_id"),
    )
    return with_web_urls_tree(
        json.dumps([node.model_dump() for node in nodes]),
        "package",
    )


async def _list_sets(c: IrisClient, args: dict[str, Any]) -> str:
    rows = await c.list_sets(collection_id=args.get("collection_id"))
    return with_web_urls_list(json.dumps([r.model_dump() for r in rows]), "set")


async def _get_set(c: IrisClient, args: dict[str, Any]) -> str:
    return with_web_url(
        (await c.get_set(args["set_id"])).model_dump_json(), "set",
    )


async def _list_collections(c: IrisClient, _args: dict[str, Any]) -> str:
    rows = await c.list_collections()
    return with_web_urls_list(json.dumps([r.model_dump() for r in rows]), "collection")


async def _get_collection(c: IrisClient, args: dict[str, Any]) -> str:
    return with_web_url(
        (await c.get_collection(args["collection_id"])).model_dump_json(), "collection",
    )


async def _export(
    c: IrisClient, args: dict[str, Any], kind: str,
) -> str:
    fmt = args.get("format", "markdown")
    method = getattr(c, f"export_{kind}")
    content: bytes = await method(args[f"{kind}_id"], format=fmt)
    return content.decode("utf-8")


async def _apply_diagram_creation(c: IrisClient, args: dict[str, Any]) -> str:
    resp = await c.apply_diagram_creation(
        args["set_id"], args["diagrams_json"], package_id=args.get("package_id"),
    )
    return resp.model_dump_json()


async def _list_response_format_types(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-157 (v5.12.0): list response-format / creation-format types.

    `purpose` defaults to `response_format` (existing behaviour);
    `creation_format` lists the (notation, diagram_type) pairs that
    have authored creation_format prompts so a local-AI MCP client
    can pick a target for diagram drafting (ADR-162, v5.17.0).
    """
    items = await c.list_response_format_types(
        purpose=args.get("purpose", "response_format"),
    )
    return json.dumps([item.model_dump() for item in items])


async def _get_response_prompt(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-157 (v5.12.0); ADR-162 (v5.17.0): fetch the composed prompt
    cascade for a (notation, diagram_type) pair.

    `purpose='response_format'` (default) returns the output-shape
    rules. `purpose='creation_format'` returns the layered creation
    cascade — Iris AI uses this server-side when generating diagrams;
    a local-AI MCP client uses it to drive `create_diagram`.
    """
    resp = await c.get_response_prompt(
        args["notation"],
        diagram_type=args.get("diagram_type"),
        purpose=args.get("purpose", "response_format"),
    )
    return resp.model_dump_json()


# v6.0.0 (ADR-164): _save_doview_analysis removed. Use create_diagram(
# notation='markdown', diagram_type='doview_analysis', ...) instead.


async def _create_collection(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-161 (v5.16.0): create a new Collection.

    v6.0.15 (ADR-175): response decorated with `web_url` via
    `with_web_url` so the model can link the user straight to the new
    entity in the Iris UI. Previously, the create_* tools returned the
    bare entity dict and the model had to guess the host.
    """
    try:
        result = await c.create_collection(
            name=args["name"],
            description=args.get("description"),
        )
    except IrisAuthError:
        return _auth_required_payload("Create collection")
    return with_web_url(result.model_dump_json(), "collection")


async def _create_set(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-161 (v5.16.0): create a new Set.

    v6.0.15 (ADR-175): response decorated with `web_url`."""
    try:
        result = await c.create_set(
            name=args["name"],
            collection_id=args.get("collection_id"),
            description=args.get("description"),
        )
    except IrisAuthError:
        return _auth_required_payload("Create set")
    return with_web_url(result.model_dump_json(), "set")


async def _create_package(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-161 (v5.16.0): create a new Package.

    v6.0.15 (ADR-175): response decorated with `web_url`."""
    try:
        result = await c.create_package(
            name=args["name"],
            set_id=args.get("set_id"),
            parent_package_id=args.get("parent_package_id"),
            description=args.get("description"),
            metadata=args.get("metadata"),
        )
    except IrisAuthError:
        return _auth_required_payload("Create package")
    return with_web_url(result.model_dump_json(), "package")


async def _create_elements(c: IrisClient, args: dict[str, Any]) -> str:
    """v6.10.0 / ADR-200: bulk create elements in one MCP call.

    Avoids N round-trips when ingesting many items (e.g. a grocery
    list). Per-item failure isolation — a bad row reports an index +
    reason without sinking the rest of the batch.
    """
    body = {"elements": args.get("elements") or []}
    try:
        resp = await c._request(
            "POST", "/api/batch/elements/create", json=body,
        )
    except IrisAuthError:
        return _auth_required_payload("Create elements (batch)")
    return json.dumps(resp.json())


async def _update_elements(c: IrisClient, args: dict[str, Any]) -> str:
    """v6.10.0 / ADR-200: bulk update elements in one MCP call.

    Each update item carries its own ``element_id`` + ``expected_version``;
    version conflicts surface as per-item failures (not whole-batch).
    """
    body = {"updates": args.get("updates") or []}
    try:
        resp = await c._request(
            "POST", "/api/batch/elements/update", json=body,
        )
    except IrisAuthError:
        return _auth_required_payload("Update elements (batch)")
    return json.dumps(resp.json())


async def _create_element(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-178 (v6.4.0): create a standalone Element.

    Elements created this way are not bound to a diagram — they exist
    in the set's element pool. To draw an element onto a diagram, use
    `apply_diagram_creation` (which materialises elements + their
    diagram representation atomically) or create the diagram with an
    inline element via `create_diagram` data payload.

    v6.8.0 (ADR-191): when ``template_id`` is supplied, the named
    template pre-fills any whitelisted fields that the caller hasn't
    set explicitly.
    """
    body: dict[str, Any] = {}
    if args.get("element_type") is not None:
        body["element_type"] = args["element_type"]
    if args.get("name") is not None:
        body["name"] = args["name"]
    for key in (
        "description", "data", "set_id", "metadata", "notation",
        "package_id", "template_id",
    ):
        if args.get(key) is not None:
            body[key] = args[key]
    try:
        resp = await c._request("POST", "/api/elements", json=body)
    except IrisAuthError:
        return _auth_required_payload("Create element")
    return with_web_url(json.dumps(resp.json()), "element")


# ── Element templates (v6.8.0, ADR-191) ──────────────────────────────


async def _create_element_template(c: IrisClient, args: dict[str, Any]) -> str:
    """v6.8.0 (ADR-191): capture a template from an existing element.

    ``included_fields`` selects which element fields the template
    carries (whitelist: name, description, element_type, notation,
    data, metadata, package_id, tags). Templates are set-scoped by
    default; pass ``is_global=true`` to make a template visible from
    any set (in which case omit ``set_id``).
    """
    body: dict[str, Any] = {
        "source_element_id": args["source_element_id"],
        "name": args["name"],
        "included_fields": args["included_fields"],
        "is_global": bool(args.get("is_global", False)),
    }
    if args.get("description") is not None:
        body["description"] = args["description"]
    if args.get("set_id") is not None:
        body["set_id"] = args["set_id"]
    try:
        resp = await c._request(
            "POST", "/api/element-templates", json=body,
        )
    except IrisAuthError:
        return _auth_required_payload("Create element template")
    return with_web_url(json.dumps(resp.json()), "element-template")


async def _list_element_templates(c: IrisClient, args: dict[str, Any]) -> str:
    """v6.8.0 (ADR-191): list element templates with set + global scope."""
    params: dict[str, Any] = {
        "page": int(args.get("page", 1)),
        "page_size": int(args.get("limit", 50)),
        "include_global": bool(args.get("include_global", True)),
    }
    if args.get("set_id") is not None:
        params["set_id"] = args["set_id"]
    try:
        resp = await c._request(
            "GET", "/api/element-templates", params=params,
        )
    except IrisAuthError:
        return _auth_required_payload("List element templates")
    return with_web_urls_list(
        json.dumps(resp.json().get("items", [])), "element-template",
    )


async def _get_element_template(c: IrisClient, args: dict[str, Any]) -> str:
    """v6.8.0 (ADR-191): fetch a single template by ID."""
    try:
        resp = await c._request(
            "GET", f"/api/element-templates/{args['template_id']}",
        )
    except IrisAuthError:
        return _auth_required_payload("Get element template")
    return with_web_url(json.dumps(resp.json()), "element-template")


async def _update_element_template(c: IrisClient, args: dict[str, Any]) -> str:
    """v6.8.0 (ADR-191): edit a template (no If-Match — templates are
    not versioned). Only the keys present in ``args`` are sent."""
    template_id = args["template_id"]
    body: dict[str, Any] = {}
    for key in ("name", "description", "included_fields", "is_global"):
        if key in args and args[key] is not None:
            body[key] = args[key]
    # set_id is tri-state-friendly: caller may pass None to mean
    # "clear" (for a global template), or a string to set.
    if "set_id" in args:
        body["set_id"] = args["set_id"]
    try:
        resp = await c._request(
            "PUT", f"/api/element-templates/{template_id}", json=body,
        )
    except IrisAuthError:
        return _auth_required_payload("Update element template")
    return with_web_url(json.dumps(resp.json()), "element-template")


async def _delete_element_template(c: IrisClient, args: dict[str, Any]) -> str:
    """v6.8.0 (ADR-191): soft-delete a template."""
    try:
        await c._request(
            "DELETE", f"/api/element-templates/{args['template_id']}",
        )
    except IrisAuthError:
        return _auth_required_payload("Delete element template")
    return json.dumps({
        "success": True, "template_id": args["template_id"], "deleted": True,
    })


async def _create_diagram(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-162 (v5.17.0): generic save for a new diagram of any
    (notation, diagram_type) pair. The caller is expected to have
    fetched the creation cascade for the chosen pair, run the guided
    conversation with the user, composed the `data` payload locally,
    and confirmed a destination. See the tool's description for the
    full workflow.

    v6.0.15 (ADR-175): response decorated with `web_url`."""
    try:
        diagram = await c.create_diagram(
            diagram_type=args["diagram_type"],
            notation=args.get("notation"),
            name=args["name"],
            data=args.get("data"),
            set_id=args["set_id"],
            parent_package_id=args.get("parent_package_id"),
            description=args.get("description"),
        )
    except IrisAuthError:
        return _auth_required_payload("Create diagram")
    return with_web_url(diagram.model_dump_json(), "diagram")


async def _list_notations(c: IrisClient, _args: dict[str, Any]) -> str:
    """ADR-162 (v5.17.0): list the registered notations
    (simple / uml / archimate / c4 / doview / markdown / bpmn) so a
    local-AI MCP client can discover what's authorable. Wraps the
    existing /api/registry/notations endpoint."""
    response = await c._request("GET", "/api/registry/notations")
    return json.dumps(response.json())


async def _list_diagram_types(c: IrisClient, _args: dict[str, Any]) -> str:
    """ADR-162 (v5.17.0): list the registered diagram_types with their
    compatible notation_ids (from diagram_type_notations). Wraps the
    existing /api/registry/diagram-types endpoint. The `notations`
    field on each row tells callers which notations are compatible —
    use this to filter the (notation, diagram_type) pair space."""
    response = await c._request("GET", "/api/registry/diagram-types")
    return json.dumps(response.json())


# v6.0.0 (ADR-164): _iris_authenticate removed. OAuth (RFC 7591/8414/9728)
# replaces the pairing-code flow for HTTP transport. Stdio operators set
# `IRIS_TOKEN` env var to a PAT.


async def _list_conversations(c: IrisClient, args: dict[str, Any]) -> str:
    rows = await c.list_conversations(
        args["set_id"], limit=int(args.get("limit", 50)),
    )
    return json.dumps([r.model_dump() for r in rows])


# ── Phase 2 render tools (ADR-179, v6.2.0) ────────────────────────────


def _attach_artefact_url(body: dict[str, Any], client_url: str) -> dict[str, Any]:
    """Attach the backend `web_url` for an artefact response.

    Artefacts are served by the backend at `/api/artefacts/<id>` (not
    by the frontend) — the URL has Content-Disposition: attachment
    so any client (browser, MCP, curl) downloads it directly. The
    URL points at IRIS_URL (backend), not IRIS_WEB_URL (frontend).
    """
    if not isinstance(body, dict):
        return body
    artefact_id = body.get("id")
    if isinstance(artefact_id, str) and client_url:
        body["web_url"] = f"{client_url.rstrip('/')}/api/artefacts/{artefact_id}"
    return body


async def _render_diagram(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-179 (v6.2.0): render a diagram to md/docx/pdf and store as
    an artefact in Iris. Returns the artefact metadata + download URL.

    Pair the returned `web_url` with a short label and present it to
    the user as a clickable download link. The artefact is auth-
    optional once created so the user can share the URL with anyone.
    """
    try:
        response = await c._request(
            "POST",
            f"/api/export/diagram/{args['diagram_id']}",
            json={"format": args.get("format", "md")},
        )
    except IrisAuthError:
        return _auth_required_payload("Render diagram")
    body = _attach_artefact_url(response.json(), c.url)
    return json.dumps(body)


# ── Phase 3 update_* + move_* tools (ADR-178, v6.3.0) ────────────────


async def _put_merge_partial(
    c: IrisClient, kind_path: str, entity_id: str,
    partial: dict[str, Any], updatable_fields: tuple[str, ...],
) -> Any:
    """PUT to /api/<kind_path>/<id> with a full body assembled from the
    current entity + caller-supplied partial overrides.

    Backend update endpoints do FULL-replace (omitting a field sets it
    to NULL), so a true partial update needs a GET + merge first. We
    fetch the current entity, copy the listed `updatable_fields`, then
    apply any non-None override from `partial`. None means "don't
    change" — to explicitly clear a field, callers need a separate
    affordance (out of scope for Phase 3).

    Costs one extra GET per update. Trade-off for partial-update UX
    without a backend PATCH refactor.

    Versioned entities (elements / diagrams / packages) require an
    ``If-Match`` header carrying the current version — backend rejects
    without it (HTTP 428). The GET we already do supplies the value;
    we add the header when ``current_version`` is present in the
    response. Unversioned endpoints (collections, sets) don't include
    the field and don't require the header.
    """
    current_resp = await c._request("GET", f"/api/{kind_path}/{entity_id}")
    current = current_resp.json()
    body: dict[str, Any] = {}
    for field in updatable_fields:
        if field in partial and partial[field] is not None:
            body[field] = partial[field]
        elif field in current:
            body[field] = current[field]
    headers: dict[str, str] | None = None
    if "current_version" in current:
        headers = {"If-Match": str(current["current_version"])}
    return await c._request(
        "PUT", f"/api/{kind_path}/{entity_id}", json=body, headers=headers,
    )


_COLLECTION_UPDATE_FIELDS = (
    "name", "description", "thumbnail_source", "thumbnail_diagram_id",
    "system_prompt", "mcp_system_context",
)
_SET_UPDATE_FIELDS = (
    "name", "description", "thumbnail_source", "thumbnail_diagram_id",
    "collection_id", "system_prompt", "mcp_system_context",
    # ADR-202 (v6.13.0): per-set hierarchy sort preference. Forwarded
    # through _put_merge_partial so MCP clients can read the current
    # value and override it, or leave it alone by omitting.
    "hierarchy_sort",
)
_SET_METADATA_FIELDS = tuple(f for f in _SET_UPDATE_FIELDS if f != "collection_id")
_PACKAGE_UPDATE_FIELDS = ("name", "description", "metadata")
_DIAGRAM_UPDATE_FIELDS = ("name", "description", "data", "metadata", "change_summary")
_ELEMENT_UPDATE_FIELDS = ("name", "description", "data")
_ELEMENT_UPDATE_FIELDS_WITH_PACKAGE = (
    "name", "description", "data", "package_id",
)


async def _update_collection(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-178 (v6.3.0): update a Collection's metadata."""
    try:
        resp = await _put_merge_partial(
            c, "collections", args["collection_id"],
            args, _COLLECTION_UPDATE_FIELDS,
        )
    except IrisAuthError:
        return _auth_required_payload("Update collection")
    return with_web_url(json.dumps(resp.json()), "collection")


async def _update_set(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-178 (v6.3.0): update a Set's metadata (excluding
    collection_id — use `move_set` for cross-collection moves)."""
    try:
        resp = await _put_merge_partial(
            c, "sets", args["set_id"],
            args, _SET_METADATA_FIELDS,
        )
    except IrisAuthError:
        return _auth_required_payload("Update set")
    return with_web_url(json.dumps(resp.json()), "set")


async def _update_package(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-178 (v6.3.0): update a Package's metadata."""
    try:
        resp = await _put_merge_partial(
            c, "packages", args["package_id"],
            args, _PACKAGE_UPDATE_FIELDS,
        )
    except IrisAuthError:
        return _auth_required_payload("Update package")
    return with_web_url(json.dumps(resp.json()), "package")


async def _update_diagram(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-178 (v6.3.0): update a Diagram's metadata or canvas data.
    Versioned — every successful update increments current_version."""
    try:
        resp = await _put_merge_partial(
            c, "diagrams", args["diagram_id"],
            args, _DIAGRAM_UPDATE_FIELDS,
        )
    except IrisAuthError:
        return _auth_required_payload("Update diagram")
    return with_web_url(json.dumps(resp.json()), "diagram")


async def _update_element(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-178 (v6.3.0): update an Element's metadata or data.

    ADR-184 (v6.7.0): also accepts ``package_id`` (set / clear via JSON
    null). Because the standard ``_put_merge_partial`` helper drops
    ``None`` overrides, ``package_id`` is wired through a small special
    case so the caller can explicitly clear membership.
    """
    try:
        # Special-case ``package_id``: only forward to the body if the
        # caller actually supplied the key (including JSON null).
        if "package_id" in args:
            current_resp = await c._request(
                "GET", f"/api/elements/{args['element_id']}",
            )
            current = current_resp.json()
            body: dict[str, Any] = {}
            for field in _ELEMENT_UPDATE_FIELDS:
                if field in args and args[field] is not None:
                    body[field] = args[field]
                elif field in current:
                    body[field] = current[field]
            body["package_id"] = args["package_id"]
            headers = {"If-Match": str(current.get("current_version", 1))}
            resp = await c._request(
                "PUT", f"/api/elements/{args['element_id']}",
                json=body, headers=headers,
            )
        else:
            resp = await _put_merge_partial(
                c, "elements", args["element_id"],
                args, _ELEMENT_UPDATE_FIELDS,
            )
    except IrisAuthError:
        return _auth_required_payload("Update element")
    return with_web_url(json.dumps(resp.json()), "element")


async def _list_package_elements(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-184 (v6.7.0): list elements that belong to a package."""
    try:
        resp = await c._request(
            "GET",
            f"/api/packages/{args['package_id']}/elements",
            params={
                "page": int(args.get("page", 1)),
                "page_size": int(args.get("limit", 50)),
            },
        )
    except IrisAuthError:
        return _auth_required_payload("List package elements")
    return with_web_urls_list(
        json.dumps(resp.json().get("items", [])), "element",
    )


async def _move_diagram(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-178 (v6.3.0): re-parent a Diagram within its current set.
    parent_package_id=None moves it to the set's root."""
    try:
        resp = await c._request(
            "PUT", f"/api/diagrams/{args['diagram_id']}/parent",
            json={"parent_package_id": args.get("parent_package_id")},
        )
    except IrisAuthError:
        return _auth_required_payload("Move diagram")
    return with_web_url(json.dumps(resp.json()), "diagram")


async def _move_package(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-178 (v6.3.0): re-parent a Package within its current set.
    parent_package_id=None moves it to the set's root. Backend
    cycle-checks."""
    try:
        resp = await c._request(
            "PUT", f"/api/packages/{args['package_id']}/parent",
            json={"parent_package_id": args.get("parent_package_id")},
        )
    except IrisAuthError:
        return _auth_required_payload("Move package")
    return with_web_url(json.dumps(resp.json()), "package")


async def _move_set(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-178 (v6.3.0): move a Set to a different (or no) Collection.

    `collection_id=None` un-groups the set. Special-cased because the
    partial-merge helper drops None overrides — for move_set, None is
    a meaningful "no collection" value, not "leave unchanged".
    """
    set_id = args["set_id"]
    try:
        current = await c._request("GET", f"/api/sets/{set_id}")
        current_json = current.json()
        body: dict[str, Any] = {}
        for field in _SET_UPDATE_FIELDS:
            if field == "collection_id":
                # Always overlay collection_id, even if None.
                body["collection_id"] = args.get("collection_id")
            elif field in current_json:
                body[field] = current_json[field]
        resp = await c._request("PUT", f"/api/sets/{set_id}", json=body)
    except IrisAuthError:
        return _auth_required_payload("Move set")
    return with_web_url(json.dumps(resp.json()), "set")


async def _render_markdown(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-179 (v6.2.0): render ad-hoc markdown content to md/docx/pdf
    and store as an artefact in Iris. Used by the creation cascade
    when the user picks 'Chat with downloadable artefacts'. Returns
    the artefact metadata + download URL.

    The cascade calls this once per selected format (markdown / docx
    / pdf). Each call returns a distinct artefact_id and web_url —
    present all returned URLs together as a list of download links.
    """
    try:
        response = await c._request(
            "POST",
            "/api/export/markdown",
            json={
                "markdown": args["markdown"],
                "title": args.get("title", "Untitled"),
                "format": args.get("format", "md"),
            },
        )
    except IrisAuthError:
        return _auth_required_payload("Render markdown")
    body = _attach_artefact_url(response.json(), c.url)
    return json.dumps(body)


TOOLS: list[Tool] = [
    Tool(
        name="search",
        description=(
            "Full-text search across Iris entities (elements, diagrams, packages, "
            "sets, collections). Use when the user wants to locate something by "
            "name or keyword before reading or editing it."
        ),
        input_schema=_schema({
            "query": _str_arg("query", "Search query string"),
            "set_id": _str_arg("set_id", "Scope to a single set", required=False),
            "collection_id": _str_arg(
                "collection_id", "Scope to a collection", required=False,
            ),
            "limit": (
                {"type": "integer", "description": "Max results", "default": 25},
                False,
            ),
        }),
        handler=_search,
    ),
    Tool(
        name="list_diagrams",
        description=(
            "List diagrams, optionally scoped to a set and filtered "
            "by parent package. Paginated — defaults to page=1, "
            "page_size=50 (max 100). Sets with more than 50 diagrams "
            "REQUIRE iterating pages, or you will miss content. "
            "Use `parent_package_id` to filter: pass the literal "
            "string \"null\" (not JSON null) to restrict to "
            "root-level diagrams (no parent package — useful for "
            "Sets whose orient sheet brackets the parts with "
            "Introduction / Conclusion markdown diagrams); pass a "
            "package id to restrict to that package's direct diagram "
            "children; omit for no parent filter."
        ),
        input_schema=_schema({
            "set_id": _str_arg("set_id", "Scope to a set", required=False),
            "parent_package_id": _str_arg(
                "parent_package_id",
                "Filter by parent package. Literal string \"null\" "
                "restricts to root-level (no parent); a package id "
                "restricts to that package's direct diagram children.",
                required=False,
            ),
            "page": (
                {"type": "integer", "description": "Page number (1-indexed)", "default": 1, "minimum": 1},
                False,
            ),
            "page_size": (
                {"type": "integer", "description": "Results per page (max 100)", "default": 50, "minimum": 1, "maximum": 100},
                False,
            ),
        }),
        handler=_list_diagrams,
    ),
    Tool(
        name="get_diagram",
        description="Fetch a diagram's metadata and canvas data by id.",
        input_schema=_schema({
            "diagram_id": _str_arg("diagram_id", "Diagram id"),
        }),
        handler=_get_diagram,
    ),
    Tool(
        name="list_elements",
        description=(
            "List elements, optionally scoped to a set and/or a package "
            "(ADR-184). Pass package_id=\"null\" to list elements with no "
            "package membership."
        ),
        input_schema=_schema({
            "set_id": _str_arg("set_id", "Scope to a set", required=False),
            "package_id": _str_arg(
                "package_id",
                'Scope to a package. Pass "null" to list unmembered elements.',
                required=False,
            ),
        }),
        handler=_list_elements,
    ),
    Tool(
        name="list_package_elements",
        description=(
            "List elements belonging to a specific package (ADR-184). "
            "Paginated — defaults to page=1, limit=50."
        ),
        input_schema=_schema({
            "package_id": _str_arg("package_id", "Package id"),
            "limit": (
                {"type": "integer", "description": "Page size (default 50)"},
                False,
            ),
            "page": (
                {"type": "integer", "description": "Page number, 1-based"},
                False,
            ),
        }),
        handler=_list_package_elements,
    ),
    Tool(
        name="get_element",
        description="Fetch an element's metadata by id.",
        input_schema=_schema({
            "element_id": _str_arg("element_id", "Element id"),
        }),
        handler=_get_element,
    ),
    Tool(
        name="list_packages",
        description=(
            "List packages, optionally scoped to a set or collection. "
            "Paginated — defaults to page=1, page_size=50 (max 100). "
            "Sets with more than 50 packages REQUIRE iterating pages, "
            "or you will miss content. For a structural overview of "
            "an entire set in one call, prefer `package_hierarchy` "
            "instead. Use `parent_package_id` to filter to direct "
            "children of a specific package; pass `parent_package_id` "
            "as omitted to get all packages (including children at "
            "every depth, in updated_at DESC order). Set's "
            "`package_count_root` and `package_count` fields on "
            "`get_set` indicate how many to expect."
        ),
        input_schema=_schema({
            "set_id": _str_arg("set_id", "Scope to a set", required=False),
            "collection_id": _str_arg(
                "collection_id", "Scope to a collection", required=False,
            ),
            "parent_package_id": _str_arg(
                "parent_package_id",
                "Filter to direct children of this package id",
                required=False,
            ),
            "page": (
                {"type": "integer", "description": "Page number (1-indexed)", "default": 1, "minimum": 1},
                False,
            ),
            "page_size": (
                {"type": "integer", "description": "Results per page (max 100)", "default": 50, "minimum": 1, "maximum": 100},
                False,
            ),
        }),
        handler=_list_packages,
    ),
    Tool(
        name="package_hierarchy",
        description=(
            "Return the complete package tree for a set as nested "
            "PackageHierarchyNode objects in a SINGLE call (ADR-158, "
            "v5.13.0). Prefer this over `list_packages` whenever you "
            "want a structural overview / chapter list / table-of-"
            "contents — `list_packages` paginates and big sets miss "
            "older chapters. The response is the list of root nodes; "
            "each node carries `id`, `name`, `parent_package_id`, "
            "`children`. Use `root_id` to scope to a sub-tree."
        ),
        input_schema=_schema({
            "set_id": _str_arg("set_id", "Scope to a set", required=False),
            "root_id": _str_arg(
                "root_id",
                "Optional sub-tree root: only return descendants of this package",
                required=False,
            ),
        }),
        handler=_package_hierarchy,
    ),
    Tool(
        name="get_package",
        description="Fetch a package by id.",
        input_schema=_schema({
            "package_id": _str_arg("package_id", "Package id"),
        }),
        handler=_get_package,
    ),
    Tool(
        name="list_sets",
        description="List sets, optionally scoped to a collection.",
        input_schema=_schema({
            "collection_id": _str_arg(
                "collection_id", "Scope to a collection", required=False,
            ),
        }),
        handler=_list_sets,
    ),
    Tool(
        name="get_set",
        description="Fetch a set by id.",
        input_schema=_schema({
            "set_id": _str_arg("set_id", "Set id"),
        }),
        handler=_get_set,
    ),
    Tool(
        name="list_collections",
        description="List every collection.",
        input_schema=_schema({}),
        handler=_list_collections,
    ),
    Tool(
        name="get_collection",
        description="Fetch a collection by id.",
        input_schema=_schema({
            "collection_id": _str_arg("collection_id", "Collection id"),
        }),
        handler=_get_collection,
    ),
    Tool(
        name="export_diagram",
        description=(
            "Export a diagram as JSON or Markdown. Use to retrieve a portable "
            "snapshot for pasting into a PR, feeding to another AI, or archiving."
        ),
        input_schema=_schema({
            "diagram_id": _str_arg("diagram_id", "Diagram id"),
            "format": ({"type": "string", "enum": ["json", "markdown"]}, True),
        }),
        handler=lambda c, a: _export(c, a, "diagram"),
    ),
    Tool(
        name="export_element",
        description="Export an element as JSON or Markdown.",
        input_schema=_schema({
            "element_id": _str_arg("element_id", "Element id"),
            "format": ({"type": "string", "enum": ["json", "markdown"]}, True),
        }),
        handler=lambda c, a: _export(c, a, "element"),
    ),
    Tool(
        name="export_package",
        description="Export a package (and all descendants) as JSON or Markdown.",
        input_schema=_schema({
            "package_id": _str_arg("package_id", "Package id"),
            "format": ({"type": "string", "enum": ["json", "markdown"]}, True),
        }),
        handler=lambda c, a: _export(c, a, "package"),
    ),
    Tool(
        name="export_set",
        description="Export a set (all packages/diagrams/elements) as JSON or Markdown.",
        input_schema=_schema({
            "set_id": _str_arg("set_id", "Set id"),
            "format": ({"type": "string", "enum": ["json", "markdown"]}, True),
        }),
        handler=lambda c, a: _export(c, a, "set"),
    ),
    Tool(
        name="export_collection",
        description="Export a collection as JSON or Markdown.",
        input_schema=_schema({
            "collection_id": _str_arg("collection_id", "Collection id"),
            "format": ({"type": "string", "enum": ["json", "markdown"]}, True),
        }),
        handler=lambda c, a: _export(c, a, "collection"),
    ),
    # v6.0.8 (ADR-168): the `ask` tool — which routed cross-scope
    # questions to Iris' server-side AI — has been removed from the MCP
    # surface. When iris-mcp is consumed by a client that has its own
    # capable LLM (claude.ai / Claude Desktop / Claude Code / Cursor),
    # routing analysis to a second AI is redundant and confusing. The
    # local model now fulfils cross-package, cross-set, and
    # cross-collection questions by reading the data directly via
    # `search`, `get_*`, `list_*`, and `package_hierarchy`. The orient
    # wrapper in `links.py` explicitly steers the model to do this.
    Tool(
        name="apply_diagram_creation",
        description=(
            "Apply a local-AI-generated diagram bundle to a set. The client "
            "drafts the diagrams JSON (one entry per diagram, matching the "
            "creation_format cascade returned by "
            "`get_response_prompt(purpose='creation_format', notation=..., "
            "diagram_type=...)`) and posts it here for persistence. "
            "Prefer `create_diagram` for single-diagram creation; this tool "
            "is for batch saves."
        ),
        input_schema=_schema({
            "set_id": _str_arg("set_id", "Target set"),
            "diagrams_json": _str_arg(
                "diagrams_json",
                "JSON payload of diagrams drafted locally per the creation "
                "cascade.",
            ),
            "package_id": _str_arg(
                "package_id", "Parent package to nest the new diagrams under",
                required=False,
            ),
        }),
        handler=_apply_diagram_creation,
    ),
    Tool(
        name="list_conversations",
        description="List the AI conversation history for a set.",
        input_schema=_schema({
            "set_id": _str_arg("set_id", "Set id"),
            "limit": (
                {"type": "integer", "description": "Max rows", "default": 50},
                False,
            ),
        }),
        handler=_list_conversations,
    ),
    # ── Response-format prompts (ADR-157, v5.12.0) ──────────────────────
    Tool(
        name="list_response_format_types",
        description=(
            "List (notation, diagram_type) pairs that have authored prompts "
            "in Iris (ADR-157, v5.12.0; ADR-162, v5.17.0). Default "
            "purpose='response_format' returns output-shape pairs (e.g. "
            "markdown/doview_analysis for formal outcomes-theory analyses). "
            "Pass purpose='creation_format' to list pairs with authored "
            "creation rules — pair with create_diagram for local-AI diagram "
            "creation."
        ),
        input_schema=_schema({
            "purpose": (
                {
                    "type": "string",
                    "enum": ["response_format", "creation_format"],
                    "default": "response_format",
                    "description": (
                        "Which prompt purpose to list. 'response_format' "
                        "(default) for output-shape rules; "
                        "'creation_format' for the drafting/composition "
                        "rules used when generating diagrams."
                    ),
                },
                False,
            ),
        }),
        handler=_list_response_format_types,
    ),
    Tool(
        name="get_response_prompt",
        description=(
            "Fetch the composed prompt cascade for a (notation, "
            "diagram_type) pair (ADR-157, v5.12.0; ADR-162, v5.17.0). "
            "Returns the layered cascade (base + notation + diagram_type) "
            "as `body`. Default purpose='response_format' returns the "
            "output-shape rules; pass purpose='creation_format' to get the "
            "drafting cascade Iris AI uses when generating a diagram — "
            "use this to drive create_diagram from a local-AI MCP client. "
            "Example: get_response_prompt(notation='doview', "
            "diagram_type='outcomes_map', purpose='creation_format') "
            "returns the Stage 0 setup questions + DoView methodology + "
            "outcomes_map layout rules."
        ),
        input_schema=_schema({
            "notation": _str_arg(
                "notation", "Notation id, e.g. 'markdown', 'doview'",
            ),
            "diagram_type": _str_arg(
                "diagram_type",
                "Diagram type id, e.g. 'doview_analysis'. Optional — when "
                "absent, returns the base + notation cascade only.",
                required=False,
            ),
            "purpose": (
                {
                    "type": "string",
                    "enum": ["response_format", "creation_format"],
                    "default": "response_format",
                    "description": (
                        "Which prompt cascade to compose. "
                        "'response_format' (default) for output-shape "
                        "rules; 'creation_format' for the drafting / "
                        "composition rules used when generating a diagram."
                    ),
                },
                False,
            ),
        }),
        handler=_get_response_prompt,
    ),
    # v6.0.0 (ADR-164): _iris_authenticate tool removed — OAuth replaces it.
    # v6.0.0 (ADR-164): save_doview_analysis removed — use create_diagram.
    # ── Entity creation (ADR-161, v5.16.0) ─────────────────────────────
    Tool(
        name="create_collection",
        description=(
            "Create a new top-level Collection in Iris (ADR-161, v5.16.0). "
            "Use after the user has confirmed they want a new collection — "
            "see the destination-confirmation guidance below. Returns the "
            "new collection's id and metadata; pass the id to "
            "create_set(collection_id=…) to nest a set inside it. Auth "
            "required (the v5.15.0 pairing flow covers this).\n\n"
            + _DESTINATION_PREAMBLE
        ),
        input_schema=_schema({
            "name": _str_arg(
                "name",
                "Display name for the new collection (1-255 chars)",
            ),
            "description": _str_arg(
                "description",
                "Optional short description shown alongside the collection",
                required=False,
            ),
        }),
        handler=_create_collection,
    ),
    Tool(
        name="create_set",
        description=(
            "Create a new Set in Iris (ADR-161, v5.16.0). Pass "
            "collection_id=… to nest under an existing collection, or "
            "omit it for a top-level (uncollected) set. Use after the "
            "user has confirmed they want a new set — see the "
            "destination-confirmation guidance below. Returns the new "
            "set's id; pass it as save_doview_analysis(set_id=…) or "
            "create_package(set_id=…). Auth required.\n\n"
            + _DESTINATION_PREAMBLE
        ),
        input_schema=_schema({
            "name": _str_arg(
                "name",
                "Display name for the new set (1-255 chars)",
            ),
            "collection_id": _str_arg(
                "collection_id",
                "Optional id of an existing collection to nest the set inside",
                required=False,
            ),
            "description": _str_arg(
                "description",
                "Optional short description shown alongside the set",
                required=False,
            ),
        }),
        handler=_create_set,
    ),
    Tool(
        name="create_package",
        description=(
            "Create a new Package in Iris (ADR-161, v5.16.0). A package "
            "is a folder inside a set used to organise multiple diagrams "
            "under a shared parent. Pass set_id=<chosen set> and "
            "parent_package_id=<parent> to nest, or omit parent_package_id "
            "for a root-level package. Use after the user has confirmed "
            "they want a new package — see the destination-confirmation "
            "guidance below. Auth required.\n\n"
            + _DESTINATION_PREAMBLE
        ),
        input_schema=_schema({
            "name": _str_arg(
                "name",
                "Display name for the new package (1-255 chars)",
            ),
            "set_id": _str_arg(
                "set_id",
                "Set this package belongs to (recommended for navigation)",
                required=False,
            ),
            "parent_package_id": _str_arg(
                "parent_package_id",
                "Optional parent package; omit for a root-level package "
                "within the set",
                required=False,
            ),
            "description": _str_arg(
                "description",
                "Optional short description shown alongside the package",
                required=False,
            ),
            "metadata": (
                {
                    "type": "object",
                    "description": (
                        "Optional metadata blob attached to the package. "
                        "Free-form; consumers may use 'order' or display "
                        "hints here."
                    ),
                    "additionalProperties": True,
                },
                False,
            ),
        }),
        handler=_create_package,
    ),
    # ── Generic diagram creation (ADR-162, v5.17.0) ─────────────────────
    Tool(
        name="list_notations",
        description=(
            "List the diagram notations registered in Iris (simple, uml, "
            "archimate, c4, doview, markdown, bpmn). Use to discover what "
            "the user can pick as a `notation` argument when creating a "
            "diagram via create_diagram (ADR-162, v5.17.0). Anonymous-"
            "readable."
        ),
        input_schema=_schema({}),
        handler=_list_notations,
    ),
    Tool(
        name="list_diagram_types",
        description=(
            "List the diagram_types registered in Iris with their "
            "compatible notations. Each entry's `notations` array tells "
            "you which notation_ids the diagram_type can be authored "
            "under (e.g. outcomes_map → doview). Use to discover what "
            "(notation, diagram_type) pair to pass to create_diagram and "
            "to get_response_prompt(purpose='creation_format') for "
            "drafting guidance (ADR-162, v5.17.0). Anonymous-readable."
        ),
        input_schema=_schema({}),
        handler=_list_diagram_types,
    ),
    Tool(
        name="create_diagram",
        description=(
            _CREATION_FLOW_PREAMBLE
            + "\n\n"
            + _DESTINATION_PREAMBLE
        ),
        input_schema=_schema({
            "set_id": _str_arg(
                "set_id",
                "Set to save the diagram under (use create_set first if "
                "the user wants a new set)",
            ),
            "name": _str_arg(
                "name",
                "Display name for the new diagram (the user's chosen title)",
            ),
            "notation": _str_arg(
                "notation",
                "Notation id from list_notations (e.g. 'doview', "
                "'markdown', 'archimate'). Optional but recommended for "
                "non-trivial diagrams.",
                required=False,
            ),
            "diagram_type": _str_arg(
                "diagram_type",
                "Diagram-type id from list_diagram_types compatible with "
                "the chosen notation (e.g. 'outcomes_map' for doview, "
                "'doview_analysis' for markdown).",
            ),
            "data": (
                {
                    "type": "object",
                    "description": (
                        "Diagram body. For visual diagrams "
                        "(doview/archimate/c4/uml/simple/bpmn): "
                        "Svelte-Flow-shaped {nodes, edges} payload "
                        "matching the layout rules in the creation "
                        "prompt. For markdown diagrams: "
                        "{\"content\": \"<markdown>\"}."
                    ),
                    "additionalProperties": True,
                },
                False,
            ),
            "parent_package_id": _str_arg(
                "parent_package_id",
                "Optional package to nest the diagram inside within the set",
                required=False,
            ),
            "description": _str_arg(
                "description",
                "Optional short description shown alongside the diagram",
                required=False,
            ),
        }),
        handler=_create_diagram,
    ),
    Tool(
        name="create_element",
        description=(
            "Create a standalone Element in a set's element pool "
            "(v6.4.0, ADR-180 follow-up). Elements created here are "
            "NOT bound to a diagram — they exist in the set's element "
            "pool and can be referenced by diagrams later. For drawing "
            "elements onto a diagram in one step, prefer "
            "`apply_diagram_creation` (atomic element + canvas "
            "materialisation) or `create_diagram` with an inline data "
            "payload. v6.8.0 (ADR-191): supply `template_id` to pre-"
            "fill whitelisted fields from a saved element template; "
            "explicit fields always win over template defaults."
        ),
        input_schema=_schema({
            "element_type": _str_arg(
                "element_type",
                "Element type (e.g. 'component', 'class', "
                "'outcome_box') — must be a registered type for the "
                "chosen notation. Optional only when `template_id` is "
                "supplied and the template includes element_type.",
                required=False,
            ),
            "name": _str_arg(
                "name",
                "Display name for the element. Optional only when "
                "`template_id` is supplied and the template includes "
                "name.",
                required=False,
            ),
            "set_id": _str_arg(
                "set_id",
                "Set to anchor the element under (optional — omitted "
                "elements live in no set)",
                required=False,
            ),
            "package_id": _str_arg(
                "package_id",
                "Optional package to attach the new element to "
                "(v6.7.4, ADR-188 / issue #154). The package must "
                "belong to the same set as `set_id`; otherwise the "
                "REST call returns 400. Saves a follow-up "
                "`update_element` call.",
                required=False,
            ),
            "notation": _str_arg(
                "notation",
                "Notation id (default 'simple'). Should match the "
                "element_type's notation.",
                required=False,
            ),
            "description": _str_arg(
                "description", "Optional description", required=False,
            ),
            "data": (
                {
                    "type": "object",
                    "description": "Optional data payload (notation-specific)",
                    "additionalProperties": True,
                },
                False,
            ),
            "metadata": (
                {"type": "object", "additionalProperties": True},
                False,
            ),
            "template_id": _str_arg(
                "template_id",
                "Optional element template (v6.8.0, ADR-191) to "
                "pre-fill whitelisted fields. Explicit request fields "
                "always win over template defaults.",
                required=False,
            ),
        }),
        handler=_create_element,
    ),
    # ── Bulk element create / update (v6.10.0, ADR-200, #173 item 6) ─────
    Tool(
        name="create_elements",
        description=(
            "Bulk-create up to 100 elements in one call (v6.10.0, "
            "ADR-200). Each item is the same shape as `create_element`'s "
            "input. Per-item failure isolation — a bad row reports an "
            "index + reason without sinking the rest of the batch. "
            "Response is a BatchResultWithIds envelope: succeeded, "
            "failed, errors[], ids[]."
        ),
        input_schema=_schema({
            "elements": (
                {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {
                        "type": "object",
                        "additionalProperties": True,
                    },
                    "description": (
                        "List of element create payloads. Each item "
                        "matches create_element: element_type, name, "
                        "description, data, set_id, package_id, "
                        "metadata, notation."
                    ),
                },
                True,
            ),
        }),
        handler=_create_elements,
    ),
    Tool(
        name="update_elements",
        description=(
            "Bulk-update up to 100 elements in one call (v6.10.0, "
            "ADR-200). Each item carries its own element_id + "
            "expected_version (per-item optimistic concurrency); "
            "version conflicts surface as per-item failures, not a "
            "whole-batch 409. Response is a BatchResultWithIds envelope."
        ),
        input_schema=_schema({
            "updates": (
                {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {
                        "type": "object",
                        "additionalProperties": True,
                    },
                    "description": (
                        "List of element update payloads. Each item "
                        "needs element_id and expected_version, plus "
                        "the same fields as update_element: name "
                        "(required), description, data, change_summary, "
                        "metadata, package_id (tri-state: omit/null/uuid)."
                    ),
                },
                True,
            ),
        }),
        handler=_update_elements,
    ),
    # ── Element templates (v6.8.0, ADR-191, issue #153) ────────────────
    Tool(
        name="create_element_template",
        description=(
            "Capture a saved template from an existing element. The "
            "template snapshots a user-chosen subset of the element's "
            "fields (whitelist: name, description, element_type, "
            "notation, data, metadata, package_id, tags) so future "
            "`create_element` calls can pre-fill from it via "
            "`template_id`. Set-scoped by default; pass "
            "`is_global=true` to share across sets (and omit "
            "`set_id`). v6.8.0, ADR-191, issue #153."
        ),
        input_schema=_schema({
            "source_element_id": _str_arg(
                "source_element_id",
                "ID of the element to snapshot the template from",
            ),
            "name": _str_arg(
                "name", "Display name for the template",
            ),
            "included_fields": (
                {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Element fields to carry into the template. "
                        "Anything outside the whitelist is dropped "
                        "silently. At least one whitelisted field is "
                        "required."
                    ),
                },
                True,
            ),
            "description": _str_arg(
                "description", "Optional template description",
                required=False,
            ),
            "set_id": _str_arg(
                "set_id",
                "Set to scope the template to. Required when "
                "`is_global` is false; must be omitted when "
                "`is_global` is true.",
                required=False,
            ),
            "is_global": (
                {
                    "type": "boolean",
                    "description": (
                        "Promote the template to global (visible from "
                        "every set). Default false."
                    ),
                    "default": False,
                },
                False,
            ),
        }),
        handler=_create_element_template,
    ),
    Tool(
        name="list_element_templates",
        description=(
            "List element templates with set + global scope. "
            "v6.8.0, ADR-191."
        ),
        input_schema=_schema({
            "set_id": _str_arg(
                "set_id",
                "Scope to a single set. Combine with "
                "`include_global=true` to also include global "
                "templates.",
                required=False,
            ),
            "include_global": (
                {
                    "type": "boolean",
                    "description": (
                        "When true (default), global templates are "
                        "included in the result."
                    ),
                    "default": True,
                },
                False,
            ),
            "page": (
                {"type": "integer", "description": "Page (1-based)",
                 "default": 1},
                False,
            ),
            "limit": (
                {"type": "integer", "description": "Page size",
                 "default": 50},
                False,
            ),
        }),
        handler=_list_element_templates,
    ),
    Tool(
        name="get_element_template",
        description=(
            "Fetch a single element template by ID. v6.8.0, ADR-191."
        ),
        input_schema=_schema({
            "template_id": _str_arg(
                "template_id", "Template ID",
            ),
        }),
        handler=_get_element_template,
    ),
    Tool(
        name="update_element_template",
        description=(
            "Edit an element template's name, description, included "
            "fields, or scope (promote to/from global). Templates "
            "are not versioned — no If-Match. When "
            "`included_fields` changes and the source element is "
            "still alive, `template_data` is re-projected from the "
            "source; otherwise the prior snapshot is filtered down "
            "to the intersection with the new fields. v6.8.0, "
            "ADR-191."
        ),
        input_schema=_schema({
            "template_id": _str_arg(
                "template_id", "Template ID",
            ),
            "name": _str_arg(
                "name", "New name", required=False,
            ),
            "description": _str_arg(
                "description", "New description", required=False,
            ),
            "included_fields": (
                {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Replacement included_fields. Triggers a "
                        "re-projection of template_data."
                    ),
                },
                False,
            ),
            "set_id": _str_arg(
                "set_id",
                "New set scope. Pass null to clear (when promoting "
                "to global).",
                required=False,
            ),
            "is_global": (
                {
                    "type": "boolean",
                    "description": (
                        "Promote to global (set_id must be null) or "
                        "demote back."
                    ),
                },
                False,
            ),
        }),
        handler=_update_element_template,
    ),
    Tool(
        name="delete_element_template",
        description=(
            "Soft-delete an element template. v6.8.0, ADR-191."
        ),
        input_schema=_schema({
            "template_id": _str_arg(
                "template_id", "Template ID",
            ),
        }),
        handler=_delete_element_template,
    ),
    # ── Phase 2 render tools (ADR-179, v6.2.0) ────────────────────────
    Tool(
        name="render_diagram",
        description=(
            "Render a diagram as markdown / docx / pdf and store the "
            "result as an Iris artefact. Returns "
            "{id, filename, mime_type, size_bytes, web_url, ...} — "
            "present the web_url to the user as a clickable download "
            "link. For markdown-content diagrams the original "
            "data.content is used directly; for visual diagrams a "
            "structured markdown summary is generated then rendered. "
            "Distinct from `export_diagram` (which returns raw JSON/"
            "markdown text) — this tool produces downloadable files."
        ),
        input_schema=_schema({
            "diagram_id": _str_arg("diagram_id", "Diagram id"),
            "format": (
                {"type": "string", "enum": ["md", "docx", "pdf"]},
                True,
            ),
        }),
        handler=_render_diagram,
    ),
    Tool(
        name="render_markdown",
        description=(
            "Render ad-hoc markdown content as markdown / docx / pdf "
            "and store the result as an Iris artefact. Used by the "
            "creation cascade when the user picks 'Chat with "
            "downloadable artefacts' — call once per selected format "
            "(md / docx / pdf). Returns {id, filename, mime_type, "
            "size_bytes, web_url, ...}. Present the web_url to the "
            "user as a clickable download link. The artefact is "
            "served at /api/artefacts/<id> with Content-Disposition: "
            "attachment so any client downloads it directly."
        ),
        input_schema=_schema({
            "markdown": _str_arg("markdown", "Markdown source text"),
            "title": _str_arg(
                "title",
                "Document title (becomes the docx/pdf heading and "
                "filename slug)",
            ),
            "format": (
                {"type": "string", "enum": ["md", "docx", "pdf"]},
                True,
            ),
        }),
        handler=_render_markdown,
    ),
    # ── Phase 3 update_* tools (ADR-178, v6.3.0) ─────────────────────
    Tool(
        name="update_collection",
        description=(
            "Update a Collection's metadata. All fields except "
            "collection_id are optional — pass only what you want to "
            "change. The backend does a full-replace under the hood; "
            "this tool fetches the current entity and merges in your "
            "partial overrides so unspecified fields are preserved. "
            "Returns the updated entity dict with web_url."
        ),
        input_schema=_schema({
            "collection_id": _str_arg("collection_id", "Collection id"),
            "name": _str_arg("name", "New name", required=False),
            "description": _str_arg("description", "New description", required=False),
            "system_prompt": _str_arg(
                "system_prompt",
                "Per-collection system prompt for Iris AI (admin-edited)",
                required=False,
            ),
            "mcp_system_context": _str_arg(
                "mcp_system_context",
                "Orient sheet body surfaced to MCP clients on read",
                required=False,
            ),
            "thumbnail_source": _str_arg(
                "thumbnail_source", "image / diagram / none", required=False,
            ),
            "thumbnail_diagram_id": _str_arg(
                "thumbnail_diagram_id",
                "Diagram id to use as thumbnail (when source=diagram)",
                required=False,
            ),
        }),
        handler=_update_collection,
    ),
    Tool(
        name="update_set",
        description=(
            "Update a Set's metadata. All fields except set_id are "
            "optional — pass only what you want to change. To move a "
            "set between collections, use `move_set` (this tool "
            "deliberately excludes the collection_id field). Returns "
            "the updated entity dict with web_url."
        ),
        input_schema=_schema({
            "set_id": _str_arg("set_id", "Set id"),
            "name": _str_arg("name", "New name", required=False),
            "description": _str_arg("description", "New description", required=False),
            "system_prompt": _str_arg(
                "system_prompt", "Per-set system prompt", required=False,
            ),
            "mcp_system_context": _str_arg(
                "mcp_system_context", "Orient sheet body", required=False,
            ),
            "thumbnail_source": _str_arg(
                "thumbnail_source", "image / diagram / none", required=False,
            ),
            "thumbnail_diagram_id": _str_arg(
                "thumbnail_diagram_id", "Thumbnail diagram id", required=False,
            ),
            "hierarchy_sort": _str_arg(
                "hierarchy_sort",
                "Hierarchy sort order for this set (v6.13.0, ADR-202). "
                "One of: 'manual' (drag-and-drop sequence_order, default), "
                "'alpha' (alphabetical by name), 'newest' (created_at DESC), "
                "'oldest' (created_at ASC). Affects every surface that renders "
                "this set's hierarchy (dashboard, packages page, views page).",
                required=False,
            ),
        }),
        handler=_update_set,
    ),
    Tool(
        name="update_package",
        description=(
            "Update a Package's metadata. Pass only the fields you "
            "want to change. To re-parent a package, use `move_package`."
        ),
        input_schema=_schema({
            "package_id": _str_arg("package_id", "Package id"),
            "name": _str_arg("name", "New name", required=False),
            "description": _str_arg("description", "New description", required=False),
            "metadata": (
                {
                    "type": "object",
                    "description": "Arbitrary metadata blob",
                    "additionalProperties": True,
                },
                False,
            ),
        }),
        handler=_update_package,
    ),
    Tool(
        name="update_diagram",
        description=(
            "Update a Diagram's metadata and/or canvas data. "
            "Versioned — every successful update increments "
            "current_version. To re-parent a diagram, use "
            "`move_diagram`. To validate edits to `data`, the backend "
            "applies the same checks as create_diagram."
        ),
        input_schema=_schema({
            "diagram_id": _str_arg("diagram_id", "Diagram id"),
            "name": _str_arg("name", "New name", required=False),
            "description": _str_arg("description", "New description", required=False),
            "data": (
                {
                    "type": "object",
                    "description": (
                        "Replacement canvas data — same shape as "
                        "create_diagram (Svelte-Flow {nodes, edges} "
                        "for visual notations; {\"content\": \"<md>\"} "
                        "for markdown)."
                    ),
                    "additionalProperties": True,
                },
                False,
            ),
            "metadata": (
                {"type": "object", "additionalProperties": True},
                False,
            ),
            "change_summary": _str_arg(
                "change_summary",
                "Optional human-readable summary of what changed",
                required=False,
            ),
        }),
        handler=_update_diagram,
    ),
    Tool(
        name="update_element",
        description=(
            "Update an Element's metadata, data, and/or package "
            "membership (ADR-184). Note: elements cannot be moved "
            "between diagrams — see ADR-178."
        ),
        input_schema=_schema({
            "element_id": _str_arg("element_id", "Element id"),
            "name": _str_arg("name", "New name", required=False),
            "description": _str_arg("description", "New description", required=False),
            "data": (
                {"type": "object", "additionalProperties": True},
                False,
            ),
            "package_id": (
                {
                    "type": ["string", "null"],
                    "description": (
                        "Set or clear the element's package membership "
                        "(ADR-184). Pass a UUID to set, JSON null to "
                        "clear, or omit to leave unchanged."
                    ),
                },
                False,
            ),
        }),
        handler=_update_element,
    ),
    # ── Phase 3 move_* tools (ADR-178, v6.3.0) ───────────────────────
    Tool(
        name="move_diagram",
        description=(
            "Re-parent a diagram within its current set. Pass "
            "parent_package_id=null to move the diagram to the set's "
            "root. Cross-set moves are NOT supported in this version "
            "— for cross-set, save into the target set directly via "
            "create_diagram. The backend cycle-checks."
        ),
        input_schema=_schema({
            "diagram_id": _str_arg("diagram_id", "Diagram id"),
            "parent_package_id": (
                {
                    "type": ["string", "null"],
                    "description": (
                        "Target package id (must be in the same set), "
                        "or null to move to set root"
                    ),
                },
                False,
            ),
        }),
        handler=_move_diagram,
    ),
    Tool(
        name="move_package",
        description=(
            "Re-parent a package within its current set. Pass "
            "parent_package_id=null to move the package to the set's "
            "root. Backend cycle-checks. Cross-set moves NOT supported."
        ),
        input_schema=_schema({
            "package_id": _str_arg("package_id", "Package id"),
            "parent_package_id": (
                {
                    "type": ["string", "null"],
                    "description": (
                        "Target package id (must be in the same set), "
                        "or null to move to set root"
                    ),
                },
                False,
            ),
        }),
        handler=_move_package,
    ),
    Tool(
        name="move_set",
        description=(
            "Move a set to a different (or no) collection. Pass "
            "collection_id=null to un-group the set so it sits at the "
            "top level. Other set metadata is preserved."
        ),
        input_schema=_schema({
            "set_id": _str_arg("set_id", "Set id"),
            "collection_id": (
                {
                    "type": ["string", "null"],
                    "description": (
                        "Target collection id, or null to un-group"
                    ),
                },
                False,
            ),
        }),
        handler=_move_set,
    ),
]


def tool_definitions() -> list[types.Tool]:
    """Return the SDK-shaped Tool objects ready for `list_tools`."""
    return [
        types.Tool(
            name=t.name, description=t.description, inputSchema=t.input_schema,
        )
        for t in TOOLS
    ]


async def dispatch(
    name: str, client: IrisClient, args: dict[str, Any],
) -> list[types.TextContent]:
    """Find and invoke the handler. Returns MCP TextContent list."""
    for tool in TOOLS:
        if tool.name == name:
            try:
                payload = await tool.handler(client, args)
                if isinstance(payload, bytes):
                    payload = payload.decode("utf-8")
                return [types.TextContent(type="text", text=payload)]
            except Exception as exc:
                return [
                    types.TextContent(
                        type="text", text=f"ERROR: {format_error(exc)}",
                    ),
                ]
    return [
        types.TextContent(
            type="text", text=f"ERROR: unknown tool '{name}'",
        ),
    ]
