"""FastAPI application factory per SPEC-004-A."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import AppConfig, get_config
from app.database import DatabaseManager
from app.startup import initialize_databases

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

    return app
