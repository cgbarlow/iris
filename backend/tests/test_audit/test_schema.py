"""Tests for audit log schema (Migration 003) in audit database."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.migrations.m003_audit_log import up

if TYPE_CHECKING:
    import aiosqlite


class TestAuditLogSchema:
    """Verify audit_log table in separate audit database."""

    async def test_audit_log_table_exists(self, audit_db: aiosqlite.Connection) -> None:
        await up(audit_db)
        cursor = await audit_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'"
        )
        assert await cursor.fetchone() is not None

    async def test_audit_log_columns(self, audit_db: aiosqlite.Connection) -> None:
        await up(audit_db)
        cursor = await audit_db.execute("PRAGMA table_info(audit_log)")
        columns = {row[1] for row in await cursor.fetchall()}
        expected = {
            "id", "timestamp", "user_id", "username", "action",
            "target_type", "target_id", "detail", "ip_address",
            "session_id", "previous_hash", "entry_hash",
        }
        assert expected == columns

    async def test_audit_log_indexes(self, audit_db: aiosqlite.Connection) -> None:
        await up(audit_db)
        cursor = await audit_db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name LIKE 'idx_audit_log%'"
        )
        indexes = {row[0] for row in await cursor.fetchall()}
        assert "idx_audit_log_timestamp" in indexes
        assert "idx_audit_log_user_id" in indexes
        assert "idx_audit_log_action" in indexes
        assert "idx_audit_log_target" in indexes

    async def test_audit_log_autoincrement_id(self, audit_db: aiosqlite.Connection) -> None:
        await up(audit_db)
        await audit_db.execute(
            "INSERT INTO audit_log "
            "(timestamp, user_id, username, action, target_type, "
            "previous_hash, entry_hash) "
            "VALUES ('2026-01-01T00:00:00Z', 'u1', 'admin', "
            "'entity.create', 'entity', 'genesis', 'hash1')"
        )
        await audit_db.commit()
        cursor = await audit_db.execute("SELECT id FROM audit_log")
        row = await cursor.fetchone()
        assert row[0] == 1

    async def test_migration_is_idempotent(self, audit_db: aiosqlite.Connection) -> None:
        await up(audit_db)
        await up(audit_db)
        cursor = await audit_db.execute(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type='table' AND name='audit_log'"
        )
        row = await cursor.fetchone()
        assert row[0] == 1
