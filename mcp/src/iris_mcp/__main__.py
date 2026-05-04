"""Stdio entry point for `iris-mcp`."""

from __future__ import annotations

import asyncio

from iris_client import IrisClient
from mcp.server import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

from iris_mcp.config import load
from iris_mcp.server import build_server


async def run() -> None:
    config = load()
    async with IrisClient(url=config.url, token=config.token) as client:
        server = build_server(client)
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
