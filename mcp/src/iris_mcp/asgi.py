"""ASGI mounting for iris-mcp (ADR-133 / SPEC-133-A).

Exposes a Streamable-HTTP ASGI application that the iris backend mounts
at `POST /mcp`. Per-request `IrisClient` binding goes through a
ContextVar so the existing stdio-oriented `tools` / `resources` modules
stay unchanged.

The stdio entry point in `__main__.py` is unaffected — it constructs a
single `IrisClient` and runs the server forever.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING

from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

from iris_mcp.server import build_server

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from iris_client import IrisClient


_current_client: ContextVar["IrisClient | None"] = ContextVar(
    "iris_current_client", default=None,
)


def get_current_client() -> "IrisClient":
    """Return the IrisClient bound to the current MCP request.

    Raises:
        RuntimeError: if called outside an MCP request scope (i.e. no
            FastAPI route has bound a client into the ContextVar).
    """
    client = _current_client.get()
    if client is None:
        msg = (
            "iris-mcp: no IrisClient bound to current request. "
            "In HTTP mode the FastAPI route must bind a client via "
            "`bind_client()` before dispatch; in stdio mode the server "
            "should be built with build_server(client) directly."
        )
        raise RuntimeError(msg)
    return client


@asynccontextmanager
async def bind_client(client: "IrisClient") -> "AsyncIterator[None]":
    """Bind `client` as the current IrisClient for the duration of the block."""
    token = _current_client.set(client)
    try:
        yield
    finally:
        _current_client.reset(token)


def build_session_manager() -> StreamableHTTPSessionManager:
    """Build a stateless Streamable HTTP session manager.

    The wrapped MCP server reads its IrisClient from the ContextVar that
    `bind_client()` populates per request. Stateless mode means no MCP-
    level session affinity — fine for our read-only + AI workload, and
    avoids the in-memory session table that would otherwise need
    eviction logic.
    """
    # _LazyClientServer reads IrisClient from the ContextVar at dispatch
    # time, so we can build the server before any request arrives.
    server = build_server(_LazyClient())  # type: ignore[arg-type]
    # json_response=True forces a single JSON response per request rather
    # than an open SSE stream — better for stateless mode and avoids
    # hung connections in clients that don't keep the SSE channel open.
    return StreamableHTTPSessionManager(
        app=server, stateless=True, json_response=True,
    )


class _LazyClient:
    """Sentinel passed to `build_server` in HTTP mode.

    `build_server` stores the argument as a closure variable used by
    every dispatch handler. In HTTP mode the real client is per-request,
    not per-server, so this sentinel proxies every attribute access
    through `get_current_client()`. The dispatch code never sees it.
    """

    def __getattr__(self, name: str) -> object:
        return getattr(get_current_client(), name)
