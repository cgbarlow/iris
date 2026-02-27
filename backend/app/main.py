"""FastAPI application factory per SPEC-004-A."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.bookmarks.router import router as bookmarks_router
from app.comments.router import router as comments_router
from app.config import AppConfig, get_config
from app.database import DatabaseManager
from app.entities.router import router as entities_router
from app.middleware.audit import AuditMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.models_crud.router import router as models_router
from app.relationships.router import router as relationships_router
from app.startup import initialize_databases
from app.users.router import router as users_router

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: initialize databases on startup, close on shutdown."""
    config: AppConfig = app.state.config
    db_manager = DatabaseManager(config.database)
    await initialize_databases(db_manager)
    app.state.db_manager = db_manager
    yield
    await db_manager.close()


def create_app(config: AppConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if config is None:
        config = get_config()

    app = FastAPI(
        title="Iris",
        description="Integrated Repository for Information & Systems",
        version="0.1.0",
        docs_url="/docs" if config.debug else None,
        redoc_url="/redoc" if config.debug else None,
    )
    app.state.config = config

    # Audit middleware per SPEC-007-A (innermost — runs after auth resolves)
    app.add_middleware(AuditMiddleware)

    # Rate limiting middleware per SPEC-005-B
    app.add_middleware(
        RateLimitMiddleware,
        login=config.rate_limit_login,
        refresh=config.rate_limit_refresh,
        general=config.rate_limit_general,
    )

    # CORS middleware per SPEC-004-A
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=3600,
    )

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
    app.include_router(entities_router)
    app.include_router(relationships_router)
    app.include_router(models_router)
    app.include_router(users_router)
    app.include_router(comments_router)
    app.include_router(bookmarks_router)

    return app
