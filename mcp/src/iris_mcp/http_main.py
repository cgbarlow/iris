"""Standalone HTTP entry point for iris-mcp (ADR-134 / SPEC-134-A).

Runs iris-mcp as a separate Render service rather than mounted on the
iris backend, so the backend doesn't carry the MCP SDK's memory
footprint (which OOM-killed the 512 MB free dyno during the embedded-
mount experiment in ADR-133). Reaches the iris backend over HTTP via
the `IRIS_API_URL` env var.

Run: `uvicorn iris_mcp.http_main:create_app --factory --host 0.0.0.0`.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from fastapi.responses import Response
from iris_client import IrisClient

from iris_mcp.asgi import bind_client, build_session_manager, extract_bearer
from iris_mcp.branding import ICON_SVG

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Build the standalone iris-mcp FastAPI app.

    Raises:
        RuntimeError: if `IRIS_API_URL` env var is not set. Refusing
            to start (rather than defaulting to localhost) makes the
            misconfiguration loud at deploy time, not at first request.
    """
    iris_url = os.environ.get("IRIS_API_URL")
    if not iris_url:
        msg = (
            "IRIS_API_URL env var required (e.g. https://iris-api-gtb3.onrender.com). "
            "This is the iris backend that iris-mcp will proxy through."
        )
        raise RuntimeError(msg)

    session_manager = build_session_manager()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        # StreamableHTTPSessionManager.run() owns the anyio task group
        # the request handler depends on; entering it for the lifetime
        # of the app is the supported pattern.
        async with session_manager.run():
            yield

    app = FastAPI(
        title="iris-mcp",
        description="Standalone Streamable-HTTP MCP server for iris (ADR-131 / ADR-133 / ADR-134).",
        lifespan=lifespan,
    )

    # Favicons must be added before the root mount, otherwise the
    # /favicon.* paths get swallowed by the catch-all ASGI app.
    @app.get("/favicon.ico", include_in_schema=False)
    @app.get("/favicon.svg", include_in_schema=False)
    async def _favicon() -> Response:
        return Response(content=ICON_SVG, media_type="image/svg+xml")

    @app.get("/info", include_in_schema=False)
    async def _info() -> dict[str, Any]:
        # Service identity for humans / health checks. NOT at "/" —
        # MCP Streamable HTTP uses GET / for session resumption and
        # streaming notifications, so any non-MCP response there
        # would clash with the protocol.
        return {
            "service": "iris-mcp",
            "endpoint": "/",
            "backend": iris_url,
        }

    async def mcp_asgi(
        scope: dict[str, Any],
        receive: "Callable[[], Awaitable[dict[str, Any]]]",
        send: "Callable[[dict[str, Any]], Awaitable[None]]",
    ) -> None:
        if scope["type"] != "http":
            return
        token = extract_bearer(scope.get("headers") or [])
        async with IrisClient(url=iris_url, token=token) as client, bind_client(client):
            await session_manager.handle_request(scope, receive, send)

    # ADR-134 follow-up: the standalone service exists solely to be
    # MCP, so mount at the root rather than at /mcp. Users paste the
    # bare service URL into Claude Desktop. No path-normalising
    # middleware needed — root mount handles every path.
    app.mount("/", mcp_asgi)

    logger.info("iris-mcp configured (backend=%s)", iris_url)
    return app
