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
  3. Run the guided conversation IN CHAT with the user. Use
     AskUserQuestion when supported; numbered list otherwise.
  4. Compose the `data` JSON locally per the creation prompt's rules.
     For visual diagrams (notation in doview / archimate / c4 / uml /
     simple / bpmn), data is a Svelte-Flow-shaped {nodes, edges}
     payload. For markdown diagrams, data is {"content": "<markdown>"}.
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
    rows = await c.list_diagrams(set_id=args.get("set_id"))
    return with_web_urls_list(json.dumps([r.model_dump() for r in rows]), "diagram")


async def _get_element(c: IrisClient, args: dict[str, Any]) -> str:
    return with_web_url(
        (await c.get_element(args["element_id"])).model_dump_json(), "element",
    )


async def _list_elements(c: IrisClient, args: dict[str, Any]) -> str:
    rows = await c.list_elements(set_id=args.get("set_id"))
    return with_web_urls_list(json.dumps([r.model_dump() for r in rows]), "element")


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
        description="List diagrams, optionally scoped to a set.",
        input_schema=_schema({
            "set_id": _str_arg("set_id", "Scope to a set", required=False),
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
        description="List elements, optionally scoped to a set.",
        input_schema=_schema({
            "set_id": _str_arg("set_id", "Scope to a set", required=False),
        }),
        handler=_list_elements,
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
