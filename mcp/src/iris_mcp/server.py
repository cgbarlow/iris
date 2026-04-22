"""MCP Server wiring for iris-mcp (SPEC-131-A).

Registers tools and resources against an injected `IrisClient`. Build
the server via `build_server(client)`; transport (stdio) is owned by
`__main__`.
"""

from __future__ import annotations

from typing import Any

from iris_client import IrisClient
from mcp import types
from mcp.server import Server

from iris_mcp import resources as iris_resources
from iris_mcp import tools as iris_tools


def build_server(client: IrisClient) -> Server:
    server: Server = Server("iris-mcp")

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

    return server
