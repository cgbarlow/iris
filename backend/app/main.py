"""FastAPI application factory per SPEC-004-A."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.ai.router import router as ai_router
from app.audit.router import router as audit_router
from app.auth.router import router as auth_router
from app.batch.router import router as batch_router
from app.bookmarks.router import router as bookmarks_router
from app.collections.router import router as collections_router
from app.comments.router import router as comments_router
from app.config import AppConfig, get_config
from app.database import DatabaseManager
from app.diagrams.registry_router import router as registry_router
from app.diagrams.router import admin_router as admin_thumbnails_router
from app.diagrams.router import diagram_rel_router
from app.diagrams.router import router as diagrams_router
from app.docref.router import router as docref_router
from app.elements.router import router as elements_router
from app.export.router import router as export_router
from app.images.router import router as images_router
from app.extensions.router import router as extensions_router
from app.graph.router import router as graph_router
from app.import_archimate.router import router as import_archimate_router
from app.import_pptx.router import router as import_pptx_router
from app.import_sparx.router import router as import_router
from app.locks.router import admin_router as admin_locks_router
from app.locks.router import router as locks_router
from app.middleware.audit import AuditMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.mnemos.router import router as mnemos_router
from app.notifications.router import router as notifications_router
from app.package_relationships.router import router as package_relationships_router
from app.packages.router import router as packages_router
from app.recycle_bin.router import router as recycle_bin_router
from app.relationships.router import router as relationships_router
from app.scenia.router import router as scenia_router
from app.search.router import router as search_router
from app.sets.router import router as sets_router
from app.settings.router import router as settings_router
from app.startup import initialize_databases
from app.themes.router import router as themes_router
from app.tokens.router import router as tokens_router
from app.tokens.service import create_pat_hasher
from app.users.router import router as users_router
from app.views.router import router as views_router

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: initialize databases on startup, close on shutdown."""
    import asyncio

    config: AppConfig = app.state.config
    db_manager = DatabaseManager(config)
    await initialize_databases(db_manager)
    app.state.db_manager = db_manager

    # Start DocRef hourly index refresh (ADR-112)
    from app.docref.scheduler import start_docref_refresh_loop

    docref_task = asyncio.create_task(start_docref_refresh_loop(app))

    # ADR-133: enter the MCP session manager's run() if /mcp was mounted.
    # This initializes the StreamableHTTP task group; without it, every
    # /mcp request fails with "Task group is not initialized."
    mcp_session_run = getattr(app.state, "mcp_session_run", None)
    if mcp_session_run is not None:
        async with mcp_session_run:
            yield
    else:
        yield

    docref_task.cancel()
    await db_manager.close()


def create_app(config: AppConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if config is None:
        config = get_config()

    app = FastAPI(
        title="Iris API",
        description=(
            "Integrated Repository for Information & Systems.\n\n"
            "Authenticate with a JWT (browser login) or a Personal Access Token "
            "(ADR-127 / see `/api/users/me/tokens`). Many read endpoints allow "
            "anonymous access (ADR-123). Rate-limit buckets are split by auth "
            "type (ADR-129).\n\n"
            "Breaking changes ship as `-v2` paths alongside deprecated originals; "
            "additive changes are made freely. See docs/api.md."
        ),
        version="0.1.0",
        # ADR-129: OpenAPI is always on at /api/docs so agents and SDK tools
        # can introspect the schema in every environment, not just debug.
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.config = config
    # Shared Argon2id hasher for PAT secret verification (ADR-127 / SPEC-127-A).
    # Built once per process so the tuned cost parameters are consistent
    # across every auth-dependency call.
    app.state.pat_hasher = create_pat_hasher(config.auth)

    # Audit middleware per SPEC-007-A (innermost — runs after auth resolves)
    app.add_middleware(AuditMiddleware)

    # Rate limiting middleware per SPEC-005-B + ADR-123 + ADR-127 + ADR-129.
    app.add_middleware(
        RateLimitMiddleware,
        login=config.rate_limit_login,
        refresh=config.rate_limit_refresh,
        general=config.rate_limit_general,
        anon_ai=config.anon_ai_rate_limit,
        pat=config.rate_limit_pat,
        anon=config.rate_limit_anon,
    )

    # CORS middleware per SPEC-004-A
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "If-Match"],
        max_age=3600,
    )

    # Suppress broken pipe errors from client disconnects (SSE streams, navigation)
    @app.middleware("http")
    async def broken_pipe_middleware(
        request: Request, call_next: object
    ) -> Response:
        try:
            return await call_next(request)  # type: ignore[misc]
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            return Response(status_code=499)  # Client closed request

    # Security headers middleware per SPEC-004-A
    @app.middleware("http")
    async def security_headers_middleware(
        request: Request, call_next: object
    ) -> Response:
        response: Response = await call_next(request)  # type: ignore[misc]
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        return response

    # Health check endpoint
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy"}

    # Register routers
    app.include_router(auth_router)
    app.include_router(elements_router)
    app.include_router(relationships_router)
    app.include_router(diagrams_router)
    app.include_router(diagram_rel_router)
    app.include_router(packages_router)
    app.include_router(users_router)
    app.include_router(comments_router)
    app.include_router(bookmarks_router)
    app.include_router(search_router)
    app.include_router(audit_router)
    app.include_router(settings_router)
    app.include_router(notifications_router)
    app.include_router(admin_thumbnails_router)
    app.include_router(import_router)
    app.include_router(images_router)
    app.include_router(import_pptx_router)
    app.include_router(import_archimate_router)
    app.include_router(package_relationships_router)
    app.include_router(sets_router)
    app.include_router(collections_router)
    app.include_router(batch_router)
    app.include_router(views_router)
    app.include_router(themes_router)
    app.include_router(recycle_bin_router)
    app.include_router(registry_router)
    app.include_router(locks_router)
    app.include_router(admin_locks_router)
    app.include_router(ai_router)
    app.include_router(extensions_router)
    app.include_router(mnemos_router)
    app.include_router(docref_router)
    app.include_router(scenia_router)
    app.include_router(graph_router)
    app.include_router(tokens_router)
    app.include_router(export_router)

    # ADR-133: optional remote MCP at /mcp. No-op if iris-mcp isn't installed.
    from app.mcp_route import attach_mcp
    attach_mcp(app)

    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:create_app", factory=True, host="0.0.0.0", port=8000)
