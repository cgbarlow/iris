"""Tool definitions for iris-mcp (SPEC-131-A).

Each entry pairs an LLM-facing description with an async handler that
calls the shared `IrisClient`. Keeping all tools in a single module means
adding/removing a capability is a one-line diff.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from iris_client import IrisClient
from mcp import types

from iris_mcp.errors import format_error
from iris_mcp.links import (
    with_web_url,
    with_web_urls_list,
    with_web_urls_search,
)


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
    rows = await c.list_packages(set_id=args.get("set_id"))
    return with_web_urls_list(json.dumps([r.model_dump() for r in rows]), "package")


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
    diagram = await c.create_diagram(
        diagram_type="doview_analysis",
        notation="markdown",
        name=args["name"],
        data={"content": args["content"]},
        set_id=args["set_id"],
        parent_package_id=args.get("parent_package_id"),
        description=args.get("description"),
    )
    return diagram.model_dump_json()


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
        description="List packages, optionally scoped to a set.",
        input_schema=_schema({
            "set_id": _str_arg("set_id", "Scope to a set", required=False),
        }),
        handler=_list_packages,
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
        name="save_doview_analysis",
        description=(
            "Persist a generated DoView analysis as a new doview_analysis "
            "diagram in Iris (ADR-157, v5.12.0). Use after the user "
            "confirms they want their formal outcomes-theory response saved. "
            "Body is markdown text (with embedded mermaid blocks where "
            "applicable). Auth required — needs IRIS_TOKEN configured on "
            "the MCP server. Returns 401-equivalent error if anonymous."
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
