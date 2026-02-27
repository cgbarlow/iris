"""Tests for database connection factory and DatabaseManager."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.config import DatabaseConfig
from app.database import DatabaseManager

if TYPE_CHECKING:
    from pathlib import Path


class TestDatabaseManager:
    """Verify DatabaseManager manages dual connections correctly."""

    async def test_connect_creates_both_databases(self, tmp_data_dir: Path) -> None:
        config = DatabaseConfig(data_dir=str(tmp_data_dir))
        manager = DatabaseManager(config)
        await manager.connect()
        try:
            assert manager.main_db is not None
            assert manager.audit_db is not None
        finally:
            await manager.close()

    async def test_main_db_has_wal_mode(self, tmp_data_dir: Path) -> None:
        config = DatabaseConfig(data_dir=str(tmp_data_dir))
        manager = DatabaseManager(config)
        await manager.connect()
        try:
            cursor = await manager.main_db.execute("PRAGMA journal_mode")
            row = await cursor.fetchone()
            assert row[0] == "wal"
        finally:
            await manager.close()

    async def test_audit_db_has_wal_mode(self, tmp_data_dir: Path) -> None:
        config = DatabaseConfig(data_dir=str(tmp_data_dir))
        manager = DatabaseManager(config)
        await manager.connect()
        try:
            cursor = await manager.audit_db.execute("PRAGMA journal_mode")
            row = await cursor.fetchone()
            assert row[0] == "wal"
        finally:
            await manager.close()

    async def test_main_db_has_foreign_keys(self, tmp_data_dir: Path) -> None:
        config = DatabaseConfig(data_dir=str(tmp_data_dir))
        manager = DatabaseManager(config)
        await manager.connect()
        try:
            cursor = await manager.main_db.execute("PRAGMA foreign_keys")
            row = await cursor.fetchone()
            assert row[0] == 1
        finally:
            await manager.close()

    async def test_close_sets_connections_to_none(self, tmp_data_dir: Path) -> None:
        config = DatabaseConfig(data_dir=str(tmp_data_dir))
        manager = DatabaseManager(config)
        await manager.connect()
        await manager.close()
        with pytest.raises(RuntimeError, match="Database not connected"):
            _ = manager.main_db

    async def test_access_before_connect_raises(self, tmp_data_dir: Path) -> None:
        config = DatabaseConfig(data_dir=str(tmp_data_dir))
        manager = DatabaseManager(config)
        with pytest.raises(RuntimeError, match="Database not connected"):
            _ = manager.main_db
        with pytest.raises(RuntimeError, match="Database not connected"):
            _ = manager.audit_db

    async def test_separate_database_files(self, tmp_data_dir: Path) -> None:
        config = DatabaseConfig(data_dir=str(tmp_data_dir))
        manager = DatabaseManager(config)
        await manager.connect()
        try:
            # Write to main_db
            await manager.main_db.execute(
                "CREATE TABLE test_table (id INTEGER PRIMARY KEY)"
            )
            await manager.main_db.commit()

            # Verify it's NOT in audit_db
            cursor = await manager.audit_db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"
            )
            row = await cursor.fetchone()
            assert row is None, "Main DB table should not appear in audit DB"
        finally:
            await manager.close()
