"""MCP Streamable HTTP route (ADR-133 / SPEC-133-A).

Mounts iris-mcp as `/mcp` on the existing FastAPI app. Per-request auth
flows through the same Bearer-token mechanism as `/api/*` (PAT or JWT
or anonymous), and the per-request `IrisClient` is bound into a
ContextVar that the MCP dispatch code reads from.

The mount is opt-in: if `iris_mcp` / `iris_client` aren't importable
(e.g. backend-only dev installs that skipped path deps) the route is
skipped with a log message and the rest of the app starts normally.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from fastapi import FastAPI

logger = logging.getLogger(__name__)


def _extract_bearer(headers: list[tuple[bytes, bytes]]) -> str | None:
    for name, value in headers:
        if name.lower() == b"authorization":
            text = value.decode("latin-1")
            prefix = "Bearer "
            if text.startswith(prefix):
                return text[len(prefix) :].strip() or None
            return None
    return None


def attach_mcp(app: FastAPI) -> None:
    """Mount iris-mcp at /mcp if the package is installable.

    Imports happen here, not at module top, so a missing iris-mcp
    install degrades gracefully — backend boots, just without /mcp.
    """
    try:
        from httpx import ASGITransport
        from iris_client import IrisClient
        from iris_mcp.asgi import bind_client, build_session_manager
    except ImportError as exc:
        logger.warning(
            "iris-mcp not installed; /mcp route disabled. "
            "Install with `pip install -e ./iris-client -e ./mcp`. (%s)",
            exc,
        )
        return

    session_manager = build_session_manager()
    # Stash the run() context so the app's lifespan can enter it.
    app.state.mcp_session_run = session_manager.run()

    async def mcp_asgi_app(
        scope: dict[str, Any],
        receive: "Callable[[], Awaitable[dict[str, Any]]]",
        send: "Callable[[dict[str, Any]], Awaitable[None]]",
    ) -> None:
        if scope["type"] != "http":
            # MCP doesn't use websocket / lifespan here; ignore.
            return
        token = _extract_bearer(scope.get("headers") or [])
        # In-process httpx transport — MCP→backend traffic stays in
        # the same Python process. Same auth header as the outer MCP
        # request, so rate-limit + audit attribute to the same user.
        transport = ASGITransport(app=app)
        async with IrisClient(
            url="http://mcp-internal", token=token, transport=transport,
        ) as client:
            async with bind_client(client):
                await session_manager.handle_request(scope, receive, send)

    app.mount("/mcp", mcp_asgi_app)
    logger.info("iris-mcp mounted at /mcp (Streamable HTTP)")
