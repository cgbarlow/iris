"""Standalone HTTP entry point for iris-mcp (ADR-134 / SPEC-134-A).

Runs iris-mcp as a separate Render service rather than mounted on the
iris backend, so the backend doesn't carry the MCP SDK's memory
footprint (which OOM-killed the 512 MB free dyno during the embedded-
mount experiment in ADR-133). Reaches the iris backend over HTTP via
the `IRIS_API_URL` env var.

Run: `uvicorn iris_mcp.http_main:create_app --factory --host 0.0.0.0`.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from fastapi.responses import Response
from iris_client import IrisClient

from iris_mcp.asgi import bind_client, build_session_manager, extract_bearer
from iris_mcp.branding import ICON_SVG
from iris_mcp.oauth_resource import build_resource_metadata
from iris_mcp.server_instructions import (
    fetch_server_instructions,
    try_fetch_server_instructions,
)

# ADR-166 (v6.0.5): default 60s between refresh ticks. Tunable via
# IRIS_MCP_INSTRUCTIONS_REFRESH_S; set to 0 to disable the loop entirely.
REFRESH_DEFAULT_S = 60.0


def _pkg_version() -> str | None:
    """v5.8.4: surface iris-mcp package version on /info so a live deploy
    can be identified by URL probe (e.g., `curl .../info`) rather than
    behaviour inference. Source of truth is `mcp/pyproject.toml`."""
    try:
        return version("iris-mcp")
    except PackageNotFoundError:
        return None

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

    # ADR-165 (v6.0.4): the orient-first protocol body (ADR-163) is
    # fetched in the lifespan startup hook below, before the first
    # request arrives. Build the session manager up front with no
    # instructions; the lifespan mutates the wrapped server's
    # `instructions` attribute once the body is in hand. Mutation is
    # safe because the MCP SDK reads `Server.instructions` per request
    # when constructing the InitializeResult — not at server-construct
    # time. Doing the fetch in the lifespan keeps create_app() sync-
    # callable from any context (including async test cases that build
    # the app inside an existing event loop).
    session_manager = build_session_manager()

    # ADR-166 (v6.0.5): how often the background refresh loop re-fetches
    # `/api/ai/server-instructions` so admin edits propagate without a
    # Render redeploy. 0 disables the loop.
    refresh_interval = float(
        os.environ.get(
            "IRIS_MCP_INSTRUCTIONS_REFRESH_S",
            str(REFRESH_DEFAULT_S),
        ),
    )

    async def _refresh_loop() -> None:
        """Periodic refresh. Preserves last-good on transient backend
        failures — `try_fetch_server_instructions` returns None instead
        of the fallback baseline, so we only write when we got a fresh
        real body."""
        while True:
            await asyncio.sleep(refresh_interval)
            fresh = await try_fetch_server_instructions(iris_url)
            if (
                fresh is not None
                and fresh != session_manager.app.instructions
            ):
                session_manager.app.instructions = fresh
                logger.info("iris-mcp: refreshed server instructions body")

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        # Mirrors the stdio wiring in __main__.py (ADR-163). Falls back
        # to the hardcoded baseline on any failure (see
        # server_instructions.py) so the HTTP transport never advertises
        # `instructions=None` in production.
        session_manager.app.instructions = await fetch_server_instructions(
            iris_url,
        )

        refresh_task: asyncio.Task[None] | None = None
        if refresh_interval > 0:
            refresh_task = asyncio.create_task(_refresh_loop())

        try:
            # StreamableHTTPSessionManager.run() owns the anyio task
            # group the request handler depends on; entering it for the
            # lifetime of the app is the supported pattern.
            async with session_manager.run():
                yield
        finally:
            if refresh_task is not None:
                refresh_task.cancel()
                try:
                    await refresh_task
                except asyncio.CancelledError:
                    pass

    app = FastAPI(
        title="iris-mcp",
        description="Standalone Streamable-HTTP MCP server for iris (ADR-131 / ADR-133 / ADR-134).",
        lifespan=lifespan,
    )
    # Expose the session manager on app.state so the v6.0.4 regression
    # tests (SPEC-165-A) can verify `instructions` reached the wrapped
    # MCP server without walking private FastAPI route internals.
    app.state.session_manager = session_manager

    # Favicons must be added before the root mount, otherwise the
    # /favicon.* paths get swallowed by the catch-all ASGI app.
    @app.get("/favicon.ico", include_in_schema=False)
    @app.get("/favicon.svg", include_in_schema=False)
    async def _favicon() -> Response:
        return Response(content=ICON_SVG, media_type="image/svg+xml")

    @app.get("/.well-known/oauth-protected-resource", include_in_schema=False)
    async def _protected_resource_metadata() -> dict[str, Any]:
        """RFC 9728 Protected Resource metadata (ADR-164, v6.0.0).

        Anonymous-readable. MCP clients fetch this on a 401 response's
        `WWW-Authenticate: Bearer resource_metadata="..."` hint and
        learn which Authorization Server to start an OAuth dance with.

        v6.0.9 (ADR-169): `authorization_server` now points at the iris
        API URL (`IRIS_API_URL`), not the frontend URL (`IRIS_WEB_URL`).
        The RFC 8414 Authorization Server metadata document and the
        `/oauth/{authorize,token,register,revoke}` endpoints all live
        on the API host. The frontend host serves a SvelteKit SPA and
        returns its index.html (HTTP 200) for unknown paths — including
        `/.well-known/oauth-authorization-server` — which silently
        broke the OAuth discovery chain. `resource` falls back to the
        API URL too (instead of the frontend URL) so it stays on the
        same host as the AS, matching the JWT `aud` semantics.
        Operators set `IRIS_MCP_PUBLIC_URL` to override `resource` with
        the canonical iris-mcp public URL when one exists.
        """
        public_url = os.environ.get("IRIS_MCP_PUBLIC_URL", "").rstrip("/")
        as_url = iris_url.rstrip("/")
        return build_resource_metadata(
            resource=public_url or as_url,
            authorization_server=as_url,
        )

    @app.get("/info", include_in_schema=False)
    async def _info() -> dict[str, Any]:
        # Service identity for humans / health checks. NOT at "/" —
        # MCP Streamable HTTP uses GET / for session resumption and
        # streaming notifications, so any non-MCP response there
        # would clash with the protocol.
        return {
            "service": "iris-mcp",
            # v5.8.4: package version pulled from importlib.metadata so
            # `curl .../info` definitively identifies the running build.
            "version": _pkg_version(),
            "endpoint": "/",
            "backend": iris_url,
            # v5.6.1: surface IRIS_WEB_URL in the info payload so an
            # operator can verify the deployment knows the front-end
            # URL it'll inject into tool responses.
            "web_url": os.environ.get("IRIS_WEB_URL"),
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
