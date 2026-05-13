"""Stdio entry point for `iris-mcp`."""

from __future__ import annotations

import asyncio
import sys

from iris_client import IrisClient
from mcp.server import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

from iris_mcp.config import load
from iris_mcp.server import build_server
from iris_mcp.server_instructions import fetch_server_instructions


async def run() -> None:
    config = load()
    # v6.0.0 (ADR-164): stdio bearer comes from IRIS_TOKEN env var only.
    # The v5.15.0 pairing-flow file fallback (~/.iris-mcp/<hash>.json)
    # is gone — HTTP transport uses OAuth, stdio uses env var.
    token = config.token or None
    source = "IRIS_TOKEN env var" if token else "anonymous"
    print(f"iris-mcp: using {source}", file=sys.stderr)
    # ADR-163 (v5.18.0): fetch the admin-editable orient-first
    # protocol from Iris and pass it through to the MCP server's
    # `instructions` field. Falls back to a hardcoded baseline if
    # the backend is unreachable.
    instructions = await fetch_server_instructions(config.url)
    async with IrisClient(url=config.url, token=token) as client:
        server = build_server(client, instructions=instructions)
        async with stdio_server() as (read, write):
            await server.run(
                read,
                write,
                InitializationOptions(
                    server_name="iris-mcp",
                    server_version="0.1.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


def run_sync() -> None:
    """Console-script entry: `iris-mcp`."""
    asyncio.run(run())


if __name__ == "__main__":
    run_sync()
