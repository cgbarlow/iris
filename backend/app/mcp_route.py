"""Optional /mcp mount on the iris backend (ADR-133, opt-in per ADR-134).

iris-mcp now ships as a standalone Render service (`iris_mcp.http_main`,
ADR-134 / SPEC-134-A) so the backend doesn't carry the MCP SDK in
resident memory. This embedded mount is preserved as a developer
convenience — set `IRIS_EMBEDDED_MCP=1` and the backend will mount
/mcp in-process. Defaults off in production.

Skipped silently when the env var is unset OR when iris-mcp /
iris-client aren't installed.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from fastapi import FastAPI

logger = logging.getLogger(__name__)


def attach_mcp(app: FastAPI) -> None:
    if os.environ.get("IRIS_EMBEDDED_MCP", "").lower() not in {"1", "true", "yes"}:
        logger.debug(
            "/mcp embedded mount disabled (set IRIS_EMBEDDED_MCP=1 to enable). "
            "Standalone iris-mcp service is the production path — see ADR-134.",
        )
        return

    try:
        from httpx import ASGITransport
        from iris_client import IrisClient
        from iris_mcp.asgi import bind_client, build_session_manager, extract_bearer
        from iris_mcp.branding import ICON_SVG
    except ImportError as exc:
        logger.warning(
            "IRIS_EMBEDDED_MCP=1 but iris-mcp not installed; /mcp disabled (%s)", exc,
        )
        return

    session_manager = build_session_manager()
    # Stash the run() context so the app's lifespan can enter it.
    app.state.mcp_session_run = session_manager.run()

    # SPEC-134-A: rewrite bare /mcp → /mcp/ before routing so we don't
    # 307; some MCP clients drop POST body when chasing redirects.
    @app.middleware("http")
    async def _normalize_mcp_path(
        request: Any, call_next: "Callable[[Any], Awaitable[Any]]",
    ) -> Any:
        if request.scope["path"] == "/mcp":
            request.scope["path"] = "/mcp/"
            request.scope["raw_path"] = b"/mcp/"
        return await call_next(request)

    async def mcp_asgi_app(
        scope: dict[str, Any],
        receive: "Callable[[], Awaitable[dict[str, Any]]]",
        send: "Callable[[dict[str, Any]], Awaitable[None]]",
    ) -> None:
        if scope["type"] != "http":
            return
        token = extract_bearer(scope.get("headers") or [])
        # In-process httpx transport — MCP→backend traffic stays in
        # the same Python process. Same auth header as the outer
        # request, so rate-limit + audit attribute to the same user.
        transport = ASGITransport(app=app)
        async with (
            IrisClient(url="http://mcp-internal", token=token, transport=transport) as client,
            bind_client(client),
        ):
            await session_manager.handle_request(scope, receive, send)

    app.mount("/mcp", mcp_asgi_app)

    # Serve the favicon at /favicon.{ico,svg} so MCP clients that
    # don't yet read serverInfo.icons can fall back to the host
    # favicon. Same SVG that ships in serverInfo.icons.
    from fastapi.responses import Response

    async def _favicon_svg() -> Response:
        return Response(content=ICON_SVG, media_type="image/svg+xml")

    app.add_api_route(
        "/favicon.svg", _favicon_svg, methods=["GET"], include_in_schema=False,
    )
    app.add_api_route(
        "/favicon.ico", _favicon_svg, methods=["GET"], include_in_schema=False,
    )

    logger.info("iris-mcp mounted at /mcp (Streamable HTTP, embedded)")
