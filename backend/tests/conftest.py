"""Shared test fixtures for Iris backend tests.

All fixtures use real temporary SQLite databases — no mocks per Protocol 9.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import aiosqlite
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import configure_connection

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from pathlib import Path


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Provide a temporary data directory for database files."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def test_config(tmp_data_dir: Path) -> AppConfig:
    """Provide test configuration with temp database paths."""
    return AppConfig(
        debug=True,
        cors_origins=["http://localhost:5173"],
        database=DatabaseConfig(data_dir=str(tmp_data_dir)),
        auth=AuthConfig(
            jwt_secret="test-secret-key-that-is-at-least-32-bytes-long-for-hs256",
            argon2_time_cost=1,
            argon2_memory_cost=8192,
            argon2_parallelism=1,
        ),
    )


@pytest.fixture
async def main_db(tmp_data_dir: Path) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Provide a configured temporary main database connection."""
    db_path = str(tmp_data_dir / "iris.db")
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await configure_connection(db)
    yield db
    await db.close()


@pytest.fixture
async def audit_db(tmp_data_dir: Path) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Provide a configured temporary audit database connection."""
    db_path = str(tmp_data_dir / "iris_audit.db")
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await configure_connection(db)
    yield db
    await db.close()
