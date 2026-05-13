"""MCP Server wiring for iris-mcp (SPEC-131-A).

Registers tools and resources against an injected `IrisClient`. Build
the server via `build_server(client)`; transport (stdio) is owned by
`__main__`.
"""

from __future__ import annotations

from typing import Any

from importlib.metadata import PackageNotFoundError, version

from iris_client import IrisClient
from mcp import types
from mcp.server import Server

from iris_mcp import prompts as iris_prompts
from iris_mcp import resources as iris_resources
from iris_mcp import tools as iris_tools
from iris_mcp.branding import iris_icon


def _package_version() -> str | None:
    try:
        return version("iris-mcp")
    except PackageNotFoundError:
        return None


def build_server(
    client: IrisClient,
    *,
    instructions: str | None = None,
) -> Server:
    """Build the iris-mcp MCP server.

    `instructions` (ADR-163, v5.18.0): the server-wide MCP
    `instructions` text returned in the InitializeResult to every
    connected MCP client. Typically the body fetched from the Iris
    backend's `GET /api/ai/server-instructions`. None disables the
    field (clients see no server-level instructions).
    """
    server: Server = Server(
        "iris-mcp",
        version=_package_version(),
        instructions=instructions,
        website_url="https://github.com/cgbarlow/iris",
        icons=[iris_icon()],
    )

    @server.list_tools()
    async def _list_tools() -> list[types.Tool]:
        return iris_tools.tool_definitions()

    @server.call_tool()
    async def _call_tool(
        name: str, arguments: dict[str, Any] | None,
    ) -> list[types.TextContent]:
        return await iris_tools.dispatch(name, client, arguments or {})

    @server.list_resources()
    async def _list_resources() -> list[types.Resource]:
        return iris_resources.resource_list()

    @server.read_resource()
    async def _read_resource(uri: types.AnyUrl) -> str:
        return await iris_resources.resource_read(str(uri), client)

    @server.list_prompts()
    async def _list_prompts() -> list[types.Prompt]:
        return await iris_prompts.list_prompts(client)

    @server.get_prompt()
    async def _get_prompt(
        name: str, arguments: dict[str, str] | None,
    ) -> types.GetPromptResult:
        return await iris_prompts.get_prompt(client, name, arguments)

    return server
