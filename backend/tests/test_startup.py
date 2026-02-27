"""Tests for database startup initialization."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.audit.service import write_audit_entry
from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.startup import initialize_databases

if TYPE_CHECKING:
    from pathlib import Path


class TestInitializeDatabases:
    """Verify startup initialization runs migrations, seeds, and verifies."""

    async def test_creates_data_directory(self, tmp_path: Path) -> None:
        data_dir = tmp_path / "newdata"
        config = AppConfig(
            database=DatabaseConfig(data_dir=str(data_dir)),
            auth=AuthConfig(
                jwt_secret="test-key-at-least-32-bytes-long-for-testing",
            ),
        )
        manager = DatabaseManager(config.database)
        await initialize_databases(manager)
        assert data_dir.exists()
        await manager.close()

    async def test_roles_seeded_after_init(self, tmp_path: Path) -> None:
        data_dir = tmp_path / "data"
        config = AppConfig(
            database=DatabaseConfig(data_dir=str(data_dir)),
            auth=AuthConfig(
                jwt_secret="test-key-at-least-32-bytes-long-for-testing",
            ),
        )
        manager = DatabaseManager(config.database)
        await initialize_databases(manager)
        cursor = await manager.main_db.execute("SELECT COUNT(*) FROM roles")
        row = await cursor.fetchone()
        assert row[0] == 4
        await manager.close()

    async def test_entities_table_exists_after_init(
        self, tmp_path: Path
    ) -> None:
        data_dir = tmp_path / "data"
        config = AppConfig(
            database=DatabaseConfig(data_dir=str(data_dir)),
            auth=AuthConfig(
                jwt_secret="test-key-at-least-32-bytes-long-for-testing",
            ),
        )
        manager = DatabaseManager(config.database)
        await initialize_databases(manager)
        cursor = await manager.main_db.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='entities'"
        )
        assert await cursor.fetchone() is not None
        await manager.close()

    async def test_audit_table_exists_after_init(
        self, tmp_path: Path
    ) -> None:
        data_dir = tmp_path / "data"
        config = AppConfig(
            database=DatabaseConfig(data_dir=str(data_dir)),
            auth=AuthConfig(
                jwt_secret="test-key-at-least-32-bytes-long-for-testing",
            ),
        )
        manager = DatabaseManager(config.database)
        await initialize_databases(manager)
        cursor = await manager.audit_db.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='audit_log'"
        )
        assert await cursor.fetchone() is not None
        await manager.close()

    async def test_audit_chain_verified_on_startup(
        self, tmp_path: Path
    ) -> None:
        data_dir = tmp_path / "data"
        config = AppConfig(
            database=DatabaseConfig(data_dir=str(data_dir)),
            auth=AuthConfig(
                jwt_secret="test-key-at-least-32-bytes-long-for-testing",
            ),
        )
        manager = DatabaseManager(config.database)
        # First init succeeds (empty chain is valid)
        await initialize_databases(manager)
        await manager.close()

    async def test_tampered_audit_chain_raises_on_startup(
        self, tmp_path: Path
    ) -> None:
        data_dir = tmp_path / "data"
        config = AppConfig(
            database=DatabaseConfig(data_dir=str(data_dir)),
            auth=AuthConfig(
                jwt_secret="test-key-at-least-32-bytes-long-for-testing",
            ),
        )
        manager = DatabaseManager(config.database)
        await initialize_databases(manager)

        # Write an audit entry then tamper with it
        await write_audit_entry(
            manager.audit_db,
            user_id="u1",
            username="admin",
            action="test",
            target_type="system",
        )
        await manager.audit_db.execute(
            "UPDATE audit_log SET entry_hash='tampered' WHERE id=1"
        )
        await manager.audit_db.commit()
        await manager.close()

        # Re-initialize should detect tampering
        manager2 = DatabaseManager(config.database)
        with pytest.raises(RuntimeError, match="Audit chain verification failed"):
            await initialize_databases(manager2)
        await manager2.close()

    async def test_idempotent_initialization(self, tmp_path: Path) -> None:
        data_dir = tmp_path / "data"
        config = AppConfig(
            database=DatabaseConfig(data_dir=str(data_dir)),
            auth=AuthConfig(
                jwt_secret="test-key-at-least-32-bytes-long-for-testing",
            ),
        )
        manager = DatabaseManager(config.database)
        await initialize_databases(manager)
        await manager.close()

        # Run again
        manager2 = DatabaseManager(config.database)
        await initialize_databases(manager2)
        cursor = await manager2.main_db.execute("SELECT COUNT(*) FROM roles")
        row = await cursor.fetchone()
        assert row[0] == 4
        await manager2.close()
