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
)
from iris_mcp.token_store import save_token


PAIRING_PAGE_PATH = "/settings/mcp-pairing"


def _pairing_url() -> str:
    """Return the user-facing URL of the MCP pairing page.

    Prefers IRIS_WEB_URL (the public web UI base) over IRIS_URL (the
    API base) when the two differ.
    """
    base = os.environ.get("IRIS_WEB_URL") or os.environ.get(
        "IRIS_URL", "http://localhost:8000",
    )
    return base.rstrip("/") + PAIRING_PAGE_PATH


def _auth_required_payload(action: str) -> str:
    """ADR-160 / SPEC-161-A: shared 401 → pairing-recovery payload.

    Every write tool (save_doview_analysis, create_collection,
    create_set, create_package) returns this exact shape on auth
    failure so the model can extract the next step uniformly:
    visit the pairing page, generate a code, call iris_authenticate.
    """
    return json.dumps({
        "success": False,
        "error": "auth_required",
        "message": (
            f"{action} failed — this MCP connection isn't"
            " authenticated yet.\n\n"
            "To fix:\n"
            f"  1. Visit {_pairing_url()}\n"
            "  2. Click 'Generate pairing code'\n"
            "  3. Paste the code back here, and I'll call iris_authenticate.\n\n"
            "(After that, this MCP connection stays authenticated"
            " for ~90 days on this machine.)"
        ),
        "pairing_url": _pairing_url(),
        "next_tool": "iris_authenticate",
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
    Prefer this over `list_packages` for structural overview."""
    nodes = await c.package_hierarchy(
        set_id=args.get("set_id"),
        root_id=args.get("root_id"),
    )
    return json.dumps([node.model_dump() for node in nodes])


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


async def _ask(c: IrisClient, args: dict[str, Any]) -> str:
    resp = await c.ask(
        args["question"],
        set_ids=args.get("set_ids"),
        collection_id=args.get("collection_id"),
        mode=args.get("mode", "discuss"),
        notation=args.get("notation"),
        thread_id=args.get("thread_id"),
    )
    return resp.model_dump_json()


async def _apply_diagram_creation(c: IrisClient, args: dict[str, Any]) -> str:
    resp = await c.apply_diagram_creation(
        args["set_id"], args["diagrams_json"], package_id=args.get("package_id"),
    )
    return resp.model_dump_json()


async def _list_response_format_types(c: IrisClient, _args: dict[str, Any]) -> str:
    """ADR-157 (v5.12.0): list response-format types available."""
    items = await c.list_response_format_types()
    return json.dumps([item.model_dump() for item in items])


async def _get_response_prompt(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-157 (v5.12.0): fetch the composed response_format prompt
    cascade for a (notation, diagram_type) pair."""
    resp = await c.get_response_prompt(
        args["notation"],
        diagram_type=args.get("diagram_type"),
    )
    return resp.model_dump_json()


async def _save_doview_analysis(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-157 (v5.12.0): persist a generated outcomes-theory analysis
    as a new `doview_analysis` diagram in Iris. Auth required —
    requires IRIS_TOKEN to be set on the MCP server."""
    try:
        diagram = await c.create_diagram(
            diagram_type="doview_analysis",
            notation="markdown",
            name=args["name"],
            data={"content": args["content"]},
            set_id=args["set_id"],
            parent_package_id=args.get("parent_package_id"),
            description=args.get("description"),
        )
    except IrisAuthError:
        # ADR-160 / SPEC-161-A: shared pairing-recovery payload.
        return _auth_required_payload("Save to Iris")
    return diagram.model_dump_json()


async def _create_collection(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-161 (v5.16.0): create a new Collection."""
    try:
        result = await c.create_collection(
            name=args["name"],
            description=args.get("description"),
        )
    except IrisAuthError:
        return _auth_required_payload("Create collection")
    return result.model_dump_json()


async def _create_set(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-161 (v5.16.0): create a new Set."""
    try:
        result = await c.create_set(
            name=args["name"],
            collection_id=args.get("collection_id"),
            description=args.get("description"),
        )
    except IrisAuthError:
        return _auth_required_payload("Create set")
    return result.model_dump_json()


async def _create_package(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-161 (v5.16.0): create a new Package."""
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
    return result.model_dump_json()


async def _iris_authenticate(c: IrisClient, args: dict[str, Any]) -> str:
    """ADR-160 (v5.15.0): authenticate this MCP connection.

    Accepts either:
      - a pairing code (`IRIS-XXXX-YYYY`) generated at /settings/mcp-pairing
      - a full PAT (`iris_pat_...`) created at /settings/tokens

    On success, persists the credential to `~/.iris-mcp/<hash>.json`
    (mode 0600) and updates the in-process IrisClient so subsequent
    tool calls in this MCP session use the new token immediately.
    """
    credential = (args.get("credential") or "").strip()
    if not credential:
        return json.dumps({
            "success": False,
            "error": "invalid_credential",
            "message": (
                "iris_authenticate requires a `credential` argument: "
                "either a pairing code (IRIS-XXXX-YYYY) or a PAT "
                "(iris_pat_...)."
            ),
        })

    iris_url = c.url

    if credential.startswith("iris_pat_"):
        # PAT-paste path: validate via /api/auth/me before persisting.
        async with IrisClient(url=iris_url, token=credential) as validator:
            try:
                await validator.whoami()
            except IrisAuthError:
                return json.dumps({
                    "success": False,
                    "error": "pat_invalid",
                    "message": (
                        "PAT is invalid or revoked. Verify it at "
                        f"{_pairing_url().replace(PAIRING_PAGE_PATH, '/settings/tokens')}."
                    ),
                })
        save_token(iris_url, credential, expires_at=None)
        c.set_token(credential)
        return json.dumps({
            "success": True,
            "mode": "pat_paste",
            "message": (
                "PAT validated and persisted. Future MCP tool calls"
                " will use this token until the PAT expires or is revoked."
            ),
        })

    code = credential.upper()
    if not code.startswith("IRIS-"):
        return json.dumps({
            "success": False,
            "error": "invalid_credential",
            "message": (
                "Credential must be a pairing code (IRIS-XXXX-YYYY) or a "
                "PAT (iris_pat_...). Generate a pairing code at "
                f"{_pairing_url()}."
            ),
        })

    # Pairing-code path: anonymous exchange.
    async with IrisClient(url=iris_url, token=None) as exchanger:
        try:
            resp = await exchanger.exchange_pairing_code(code)
        except IrisHTTPError as exc:
            if exc.status_code == 410:  # noqa: PLR2004 — backend uses 410 Gone for invalid/expired/exchanged
                return json.dumps({
                    "success": False,
                    "error": "pairing_code_unusable",
                    "message": (
                        "Pairing code is unknown, expired, or already"
                        f" exchanged. Generate a new one at {_pairing_url()}."
                    ),
                })
            raise
    save_token(iris_url, resp.token, expires_at=resp.expires_at)
    c.set_token(resp.token)
    return json.dumps({
        "success": True,
        "mode": "pairing_code",
        "expires_at": resp.expires_at,
        "message": (
            f"Authenticated and persisted. Future MCP tool calls will"
            f" use this token until {resp.expires_at}. Revoke any time"
            f" at {_pairing_url().replace(PAIRING_PAGE_PATH, '/settings/tokens')}."
        ),
    })


async def _list_conversations(c: IrisClient, args: dict[str, Any]) -> str:
    rows = await c.list_conversations(
        args["set_id"], limit=int(args.get("limit", 50)),
    )
    return json.dumps([r.model_dump() for r in rows])


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
    Tool(
        name="ask",
        description=(
            "Ask the Iris AI a question about one or more sets. Use for "
            "cross-package queries ('what services depend on Payments?'), "
            "summaries, and architectural questions that span many entities. "
            "Pair with `search` to locate entities first, or with "
            "`apply_diagram_creation` when mode='creation'."
        ),
        input_schema=_schema({
            "question": _str_arg("question", "The question"),
            "set_ids": (
                {"type": "array", "items": {"type": "string"},
                 "description": "Scope the answer to these set ids"},
                False,
            ),
            "collection_id": _str_arg(
                "collection_id", "Scope to a collection", required=False,
            ),
            "mode": (
                {"type": "string", "enum": ["discuss", "creation"],
                 "default": "discuss"},
                False,
            ),
            "notation": _str_arg(
                "notation", "Diagram notation for creation mode", required=False,
            ),
            "thread_id": _str_arg(
                "thread_id", "Continue a prior conversation", required=False,
            ),
        }),
        handler=_ask,
    ),
    Tool(
        name="apply_diagram_creation",
        description=(
            "Apply an AI-generated diagram bundle to a set. Use after calling "
            "`ask` with mode='creation' and receiving a diagrams JSON string."
        ),
        input_schema=_schema({
            "set_id": _str_arg("set_id", "Target set"),
            "diagrams_json": _str_arg(
                "diagrams_json", "JSON payload returned by `ask` in creation mode",
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
            "List response-format types available — (notation, diagram_type) "
            "pairs that have authored response_format prompts in Iris. Use "
            "to discover which formats can be applied to your response "
            "(e.g. notation='markdown' diagram_type='doview_analysis' for "
            "the formal handbook-grounded outcomes-theory analysis shape)."
        ),
        input_schema=_schema({}),
        handler=_list_response_format_types,
    ),
    Tool(
        name="get_response_prompt",
        description=(
            "Fetch the composed response_format prompt for a "
            "(notation, diagram_type) pair (ADR-157). Returns the layered "
            "cascade (base + notation + diagram_type) as `body`. Apply the "
            "body as reference for shaping your response. Use this when "
            "the user asks for a formal output style matching one of the "
            "available types from `list_response_format_types` — for "
            "DoView outcomes-theory analyses call with notation='markdown' "
            "diagram_type='doview_analysis'."
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
        }),
        handler=_get_response_prompt,
    ),
    Tool(
        name="iris_authenticate",
        description=(
            "Authenticate this Iris MCP connection (ADR-160, v5.15.0). "
            "Pass either a pairing code from Iris's web UI "
            "(/settings/mcp-pairing — short typeable IRIS-XXXX-YYYY form) "
            "or a full Personal Access Token (iris_pat_..., from "
            "/settings/tokens). The token is persisted at "
            "~/.iris-mcp/<hash>.json (mode 0600) and applied immediately "
            "to this MCP session — no client restart required. Use this "
            "tool when a write-capable Iris tool (e.g. save_doview_analysis) "
            "reports auth_required, or proactively if the user provides a "
            "pairing code."
        ),
        input_schema=_schema({
            "credential": _str_arg(
                "credential",
                "Pairing code (IRIS-XXXX-YYYY) or PAT (iris_pat_...).",
            ),
        }),
        handler=_iris_authenticate,
    ),
    Tool(
        name="save_doview_analysis",
        description=(
            "Persist a generated DoView analysis as a new doview_analysis "
            "diagram in Iris (ADR-157, v5.12.0). Body is markdown text "
            "(with embedded mermaid blocks where applicable). Auth required "
            "— use the iris_authenticate tool (ADR-160) if a previous call "
            "returned error=auth_required.\n\n"
            + _DESTINATION_PREAMBLE
        ),
        input_schema=_schema({
            "set_id": _str_arg("set_id", "Set to save the analysis under"),
            "name": _str_arg(
                "name",
                "Diagram name shown in Iris (e.g. the question or a short title)",
            ),
            "content": _str_arg(
                "content",
                "Markdown body of the analysis (Summary + Full + Diagrams sections)",
            ),
            "parent_package_id": _str_arg(
                "parent_package_id",
                "Optional package to nest this diagram under within the set",
                required=False,
            ),
            "description": _str_arg(
                "description",
                "Optional short description shown alongside the diagram",
                required=False,
            ),
        }),
        handler=_save_doview_analysis,
    ),
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
