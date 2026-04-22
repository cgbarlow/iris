"""Configuration management for Iris backend."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DatabaseConfig:
    """SQLite database configuration."""

    data_dir: str = field(default_factory=lambda: os.environ.get("IRIS_DATA_DIR", "data"))

    @property
    def main_db_path(self) -> str:
        return os.path.join(self.data_dir, "iris.db")

    @property
    def audit_db_path(self) -> str:
        return os.path.join(self.data_dir, "iris_audit.db")


@dataclass(frozen=True)
class SupabaseConfig:
    """Supabase/PostgreSQL deployment configuration (used when IRIS_DB_BACKEND=supabase)."""

    url: str
    anon_key: str
    service_role_key: str
    db_url: str
    jwt_secret: str


@dataclass(frozen=True)
class AuthConfig:
    """Authentication configuration."""

    jwt_secret: str = field(
        default_factory=lambda: os.environ.get(
            "IRIS_JWT_SECRET",
            "dev-secret-change-in-production-must-be-at-least-32-bytes-long",
        )
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    argon2_time_cost: int = 3
    argon2_memory_cost: int = 65536
    argon2_parallelism: int = 4
    max_failed_logins: int = 5
    lockout_minutes: int = 15
    min_password_length: int = 12
    max_password_length: int = 128
    password_history_count: int = 5


@dataclass(frozen=True)
class AIConfig:
    """AI provider configuration."""

    default_max_context_tokens: int = field(
        default_factory=lambda: int(os.environ.get("IRIS_AI_MAX_CONTEXT_TOKENS", "8000"))
    )
    default_timeout_ms: int = field(
        default_factory=lambda: int(os.environ.get("IRIS_AI_TIMEOUT_MS", "30000"))
    )


@dataclass(frozen=True)
class AppConfig:
    """Application configuration."""

    debug: bool = field(
        default_factory=lambda: os.environ.get("IRIS_DEBUG", "false").lower() == "true"
    )
    cors_origins: list[str] = field(
        default_factory=lambda: os.environ.get(
            "IRIS_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
        ).split(",")
    )
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    rate_limit_login: int = field(
        default_factory=lambda: int(os.environ.get("IRIS_RATE_LIMIT_LOGIN", "10"))
    )
    rate_limit_refresh: int = field(
        default_factory=lambda: int(os.environ.get("IRIS_RATE_LIMIT_REFRESH", "30"))
    )
    rate_limit_general: int = field(
        default_factory=lambda: int(os.environ.get("IRIS_RATE_LIMIT_GENERAL", "1000"))
    )
    # Anonymous AI calls (no Authorization header) get a stricter per-IP bucket
    # to bound cost exposure on a publicly-accessible UAT deployment (ADR-123).
    # Uses a 1 hour window; all other buckets use 60 s.
    anon_ai_rate_limit: int = field(
        default_factory=lambda: int(os.environ.get("IRIS_RATE_LIMIT_ANON_AI", "10"))
    )
    # PAT-authenticated calls (Authorization: Bearer iris_pat_...) — ADR-127.
    # Tuned higher than general JWT because programmatic callers (CLI, MCP,
    # agents) naturally burst but are bounded per-user by PAT ownership.
    rate_limit_pat: int = field(
        default_factory=lambda: int(os.environ.get("IRIS_RATE_LIMIT_PAT", "60"))
    )
    # Anonymous non-AI calls (ADR-129) — read endpoints opened up by ADR-123.
    rate_limit_anon: int = field(
        default_factory=lambda: int(os.environ.get("IRIS_RATE_LIMIT_ANON", "30"))
    )
    # Deployment mode: "sqlite" (default, self-hosted) or "supabase" (Netlify/Supabase cloud)
    db_backend: str = field(
        default_factory=lambda: os.environ.get("IRIS_DB_BACKEND", "sqlite")
    )
    supabase: SupabaseConfig | None = field(default=None)


def get_config() -> AppConfig:
    """Get application configuration from environment variables."""
    db_backend = os.environ.get("IRIS_DB_BACKEND", "sqlite")
    supabase: SupabaseConfig | None = None
    if db_backend == "supabase":
        supabase = SupabaseConfig(
            url=os.environ.get("SUPABASE_URL", ""),
            anon_key=os.environ.get("SUPABASE_ANON_KEY", ""),
            service_role_key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""),
            db_url=os.environ.get("SUPABASE_DB_URL", ""),
            jwt_secret=os.environ.get("SUPABASE_JWT_SECRET", ""),
        )
    return AppConfig(supabase=supabase)
