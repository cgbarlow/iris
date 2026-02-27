"""Tests for Migration 001: roles, users, and auth tables."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest

from app.migrations.m001_roles_users import up

if TYPE_CHECKING:
    import aiosqlite


class TestMigration001:
    """Verify Migration 001 creates all required tables with correct schema."""

    async def test_roles_table_exists(self, main_db: aiosqlite.Connection) -> None:
        await up(main_db)
        cursor = await main_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='roles'"
        )
        assert await cursor.fetchone() is not None

    async def test_role_permissions_table_exists(self, main_db: aiosqlite.Connection) -> None:
        await up(main_db)
        cursor = await main_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='role_permissions'"
        )
        assert await cursor.fetchone() is not None

    async def test_users_table_exists(self, main_db: aiosqlite.Connection) -> None:
        await up(main_db)
        cursor = await main_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )
        assert await cursor.fetchone() is not None

    async def test_password_history_table_exists(self, main_db: aiosqlite.Connection) -> None:
        await up(main_db)
        cursor = await main_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='password_history'"
        )
        assert await cursor.fetchone() is not None

    async def test_refresh_tokens_table_exists(self, main_db: aiosqlite.Connection) -> None:
        await up(main_db)
        cursor = await main_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='refresh_tokens'"
        )
        assert await cursor.fetchone() is not None

    async def test_users_table_columns(self, main_db: aiosqlite.Connection) -> None:
        await up(main_db)
        cursor = await main_db.execute("PRAGMA table_info(users)")
        columns = {row[1] for row in await cursor.fetchall()}
        expected = {
            "id", "username", "password_hash", "role", "is_active",
            "failed_login_count", "locked_until", "last_login_at",
            "password_changed_at", "created_at", "updated_at",
        }
        assert expected == columns

    async def test_refresh_tokens_indexes(self, main_db: aiosqlite.Connection) -> None:
        await up(main_db)
        cursor = await main_db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_refresh%'"
        )
        indexes = {row[0] for row in await cursor.fetchall()}
        assert "idx_refresh_tokens_user" in indexes
        assert "idx_refresh_tokens_family" in indexes

    async def test_roles_foreign_key_enforced(self, main_db: aiosqlite.Connection) -> None:
        await up(main_db)
        await main_db.execute(
            "INSERT INTO roles (id, name, description) VALUES ('admin', 'Admin', 'Admin role')"
        )
        await main_db.execute(
            "INSERT INTO users (id, username, password_hash, role) "
            "VALUES ('u1', 'admin', 'hash', 'admin')"
        )
        await main_db.commit()
        cursor = await main_db.execute("SELECT username FROM users WHERE id='u1'")
        row = await cursor.fetchone()
        assert row[0] == "admin"

    async def test_migration_is_idempotent(self, main_db: aiosqlite.Connection) -> None:
        await up(main_db)
        await up(main_db)  # Should not raise
        cursor = await main_db.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='users'"
        )
        row = await cursor.fetchone()
        assert row[0] == 1

    async def test_username_unique_constraint(self, main_db: aiosqlite.Connection) -> None:
        await up(main_db)
        await main_db.execute(
            "INSERT INTO roles (id, name, description) VALUES ('admin', 'Admin', 'Admin role')"
        )
        await main_db.execute(
            "INSERT INTO users (id, username, password_hash, role) "
            "VALUES ('u1', 'testuser', 'hash', 'admin')"
        )
        await main_db.commit()
        with pytest.raises(sqlite3.IntegrityError):
            await main_db.execute(
                "INSERT INTO users (id, username, password_hash, role) "
                "VALUES ('u2', 'testuser', 'hash2', 'admin')"
            )
