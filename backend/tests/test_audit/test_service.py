"""Tests for audit service — hash chain write and verify."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from app.audit.service import (
    GENESIS_HASH,
    compute_entry_hash,
    verify_audit_chain,
    write_audit_entry,
)
from app.migrations.m003_audit_log import up as m003_up

if TYPE_CHECKING:
    import aiosqlite


class TestGenesisHash:
    """Verify genesis hash is deterministic."""

    def test_genesis_hash_is_deterministic(self) -> None:
        expected = hashlib.sha256(b"IRIS_AUDIT_GENESIS").hexdigest()
        assert expected == GENESIS_HASH

    def test_genesis_hash_is_sha256(self) -> None:
        assert len(GENESIS_HASH) == 64  # SHA-256 hex = 64 chars


class TestComputeEntryHash:
    """Verify hash computation per SPEC-007-A."""

    def test_hash_is_deterministic(self) -> None:
        entry: dict[str, object] = {
            "id": 1,
            "timestamp": "2026-01-01T00:00:00Z",
            "user_id": "u1",
            "username": "admin",
            "action": "entity.create",
            "target_type": "entity",
            "target_id": "e1",
            "detail": '{"name": "test"}',
            "ip_address": "127.0.0.1",
            "session_id": "jti123",
        }
        h1 = compute_entry_hash(entry, GENESIS_HASH)
        h2 = compute_entry_hash(entry, GENESIS_HASH)
        assert h1 == h2

    def test_different_entries_produce_different_hashes(self) -> None:
        entry1: dict[str, object] = {
            "id": 1, "timestamp": "t1", "user_id": "u1",
            "username": "admin", "action": "a1", "target_type": "entity",
        }
        entry2: dict[str, object] = {
            "id": 2, "timestamp": "t2", "user_id": "u1",
            "username": "admin", "action": "a2", "target_type": "entity",
        }
        assert compute_entry_hash(entry1, GENESIS_HASH) != compute_entry_hash(
            entry2, GENESIS_HASH
        )


class TestWriteAuditEntry:
    """Verify writing hash-chained audit entries."""

    async def test_write_first_entry(self, audit_db: aiosqlite.Connection) -> None:
        await m003_up(audit_db)
        await write_audit_entry(
            audit_db,
            user_id="u1",
            username="admin",
            action="entity.create",
            target_type="entity",
            target_id="e1",
            detail={"name": "Auth Service"},
        )
        cursor = await audit_db.execute("SELECT COUNT(*) FROM audit_log")
        row = await cursor.fetchone()
        assert row[0] == 1

    async def test_first_entry_uses_genesis_hash(
        self, audit_db: aiosqlite.Connection
    ) -> None:
        await m003_up(audit_db)
        await write_audit_entry(
            audit_db,
            user_id="u1",
            username="admin",
            action="entity.create",
            target_type="entity",
        )
        cursor = await audit_db.execute(
            "SELECT previous_hash FROM audit_log WHERE id=1"
        )
        row = await cursor.fetchone()
        assert row[0] == GENESIS_HASH

    async def test_chain_links_entries(
        self, audit_db: aiosqlite.Connection
    ) -> None:
        await m003_up(audit_db)
        await write_audit_entry(
            audit_db,
            user_id="u1",
            username="admin",
            action="entity.create",
            target_type="entity",
            target_id="e1",
        )
        await write_audit_entry(
            audit_db,
            user_id="u1",
            username="admin",
            action="entity.update",
            target_type="entity",
            target_id="e1",
        )
        cursor = await audit_db.execute(
            "SELECT entry_hash FROM audit_log WHERE id=1"
        )
        first_hash = (await cursor.fetchone())[0]
        cursor = await audit_db.execute(
            "SELECT previous_hash FROM audit_log WHERE id=2"
        )
        second_prev = (await cursor.fetchone())[0]
        assert first_hash == second_prev

    async def test_entry_hash_is_computed(
        self, audit_db: aiosqlite.Connection
    ) -> None:
        await m003_up(audit_db)
        await write_audit_entry(
            audit_db,
            user_id="u1",
            username="admin",
            action="entity.create",
            target_type="entity",
        )
        cursor = await audit_db.execute(
            "SELECT entry_hash FROM audit_log WHERE id=1"
        )
        row = await cursor.fetchone()
        assert len(row[0]) == 64  # SHA-256 hex


class TestVerifyAuditChain:
    """Verify audit chain verification."""

    async def test_empty_chain_is_valid(
        self, audit_db: aiosqlite.Connection
    ) -> None:
        await m003_up(audit_db)
        valid, count = await verify_audit_chain(audit_db)
        assert valid is True
        assert count == 0

    async def test_single_entry_chain_is_valid(
        self, audit_db: aiosqlite.Connection
    ) -> None:
        await m003_up(audit_db)
        await write_audit_entry(
            audit_db,
            user_id="u1",
            username="admin",
            action="entity.create",
            target_type="entity",
        )
        valid, count = await verify_audit_chain(audit_db)
        assert valid is True
        assert count == 1

    async def test_multi_entry_chain_is_valid(
        self, audit_db: aiosqlite.Connection
    ) -> None:
        await m003_up(audit_db)
        for i in range(5):
            await write_audit_entry(
                audit_db,
                user_id="u1",
                username="admin",
                action=f"entity.{['create', 'update', 'delete'][i % 3]}",
                target_type="entity",
                target_id=f"e{i}",
            )
        valid, count = await verify_audit_chain(audit_db)
        assert valid is True
        assert count == 5

    async def test_tampered_hash_detected(
        self, audit_db: aiosqlite.Connection
    ) -> None:
        await m003_up(audit_db)
        await write_audit_entry(
            audit_db,
            user_id="u1",
            username="admin",
            action="entity.create",
            target_type="entity",
        )
        # Tamper with the entry hash
        await audit_db.execute(
            "UPDATE audit_log SET entry_hash='tampered' WHERE id=1"
        )
        await audit_db.commit()
        valid, failed_at = await verify_audit_chain(audit_db)
        assert valid is False
        assert failed_at == 1

    async def test_tampered_previous_hash_detected(
        self, audit_db: aiosqlite.Connection
    ) -> None:
        await m003_up(audit_db)
        await write_audit_entry(
            audit_db,
            user_id="u1",
            username="admin",
            action="entity.create",
            target_type="entity",
        )
        await write_audit_entry(
            audit_db,
            user_id="u1",
            username="admin",
            action="entity.update",
            target_type="entity",
        )
        # Tamper with second entry's previous_hash
        await audit_db.execute(
            "UPDATE audit_log SET previous_hash='tampered' WHERE id=2"
        )
        await audit_db.commit()
        valid, failed_at = await verify_audit_chain(audit_db)
        assert valid is False
        assert failed_at == 2
