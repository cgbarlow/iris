"""Tests for project setup — verifies directory structure, config, and database connection."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from app.config import AppConfig, get_config
from app.database import get_connection

if TYPE_CHECKING:
    from pathlib import Path

    import aiosqlite


EXPECTED_PACKAGES = [
    "app",
    "app.auth",
    "app.audit",
    "app.entities",
    "app.models",
    "app.relationships",
    "app.middleware",
    "app.migrations",
]


class TestProjectStructure:
    """Verify the project directory skeleton matches SPEC-004-A."""

    def test_all_packages_importable(self) -> None:
        for package in EXPECTED_PACKAGES:
            mod = importlib.import_module(package)
            assert mod is not None, f"Failed to import {package}"


class TestConfig:
    """Verify configuration management."""

    def test_default_config(self) -> None:
        config = get_config()
        assert isinstance(config, AppConfig)
        assert config.auth.jwt_algorithm == "HS256"
        assert config.auth.access_token_expire_minutes == 15
        assert config.auth.refresh_token_expire_days == 7
        assert config.auth.argon2_time_cost == 3
        assert config.auth.argon2_memory_cost == 65536
        assert config.auth.argon2_parallelism == 4
        assert config.auth.max_failed_logins == 5
        assert config.auth.lockout_minutes == 15
        assert config.auth.min_password_length == 12
        assert config.auth.max_password_length == 128
        assert config.auth.password_history_count == 5

    def test_database_paths(self, test_config: AppConfig) -> None:
        assert test_config.database.main_db_path.endswith("iris.db")
        assert test_config.database.audit_db_path.endswith("iris_audit.db")


class TestDatabaseConnection:
    """Verify SQLite connection factory applies all 7 PRAGMAs per SPEC-004-A."""

    async def test_wal_mode(self, main_db: aiosqlite.Connection) -> None:
        cursor = await main_db.execute("PRAGMA journal_mode")
        row = await cursor.fetchone()
        assert row[0] == "wal"

    async def test_foreign_keys_enabled(self, main_db: aiosqlite.Connection) -> None:
        cursor = await main_db.execute("PRAGMA foreign_keys")
        row = await cursor.fetchone()
        assert row[0] == 1

    async def test_busy_timeout(self, main_db: aiosqlite.Connection) -> None:
        cursor = await main_db.execute("PRAGMA busy_timeout")
        row = await cursor.fetchone()
        assert row[0] == 5000

    async def test_synchronous_normal(self, main_db: aiosqlite.Connection) -> None:
        cursor = await main_db.execute("PRAGMA synchronous")
        row = await cursor.fetchone()
        assert row[0] == 1  # NORMAL = 1

    async def test_cache_size(self, main_db: aiosqlite.Connection) -> None:
        cursor = await main_db.execute("PRAGMA cache_size")
        row = await cursor.fetchone()
        assert row[0] == -64000

    async def test_journal_size_limit(self, main_db: aiosqlite.Connection) -> None:
        cursor = await main_db.execute("PRAGMA journal_size_limit")
        row = await cursor.fetchone()
        assert row[0] == 67108864

    async def test_auto_vacuum_incremental(self, main_db: aiosqlite.Connection) -> None:
        cursor = await main_db.execute("PRAGMA auto_vacuum")
        row = await cursor.fetchone()
        assert row[0] == 2  # INCREMENTAL = 2

    async def test_audit_db_has_pragmas(self, audit_db: aiosqlite.Connection) -> None:
        cursor = await audit_db.execute("PRAGMA journal_mode")
        row = await cursor.fetchone()
        assert row[0] == "wal"

    async def test_get_connection_factory(self, tmp_data_dir: Path) -> None:
        db_path = str(tmp_data_dir / "test_factory.db")
        db = await get_connection(db_path)
        try:
            cursor = await db.execute("PRAGMA journal_mode")
            row = await cursor.fetchone()
            assert row[0] == "wal"
            cursor = await db.execute("PRAGMA foreign_keys")
            row = await cursor.fetchone()
            assert row[0] == 1
        finally:
            await db.close()
