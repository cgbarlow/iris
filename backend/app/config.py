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
class AppConfig:
    """Application configuration."""

    debug: bool = field(
        default_factory=lambda: os.environ.get("IRIS_DEBUG", "false").lower() == "true"
    )
    cors_origins: list[str] = field(
        default_factory=lambda: os.environ.get(
            "IRIS_CORS_ORIGINS", "http://localhost:5173"
        ).split(",")
    )
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    rate_limit_login: int = field(
        default_factory=lambda: int(os.environ.get("IRIS_RATE_LIMIT_LOGIN", "10"))
    )
    rate_limit_refresh: int = field(
        default_factory=lambda: int(os.environ.get("IRIS_RATE_LIMIT_REFRESH", "30"))
    )
    rate_limit_general: int = field(
        default_factory=lambda: int(os.environ.get("IRIS_RATE_LIMIT_GENERAL", "100"))
    )


def get_config() -> AppConfig:
    """Get application configuration."""
    return AppConfig()
