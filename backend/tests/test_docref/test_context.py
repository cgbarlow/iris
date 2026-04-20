"""Tests for DocRef context building (ADR-112)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.docref.service import build_docref_context
from app.startup import initialize_databases

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        debug=True,
        cors_origins=["http://localhost:5173"],
        database=DatabaseConfig(data_dir=str(tmp_path / "data")),
        auth=AuthConfig(
            jwt_secret="test-secret-key-that-is-at-least-32-bytes-long-for-hs256",
            argon2_time_cost=1,
            argon2_memory_cost=8192,
            argon2_parallelism=1,
        ),
    )


@pytest.fixture
async def db(app_config: AppConfig):
    db_manager = DatabaseManager(app_config)
    await initialize_databases(db_manager)
    yield db_manager.main_db
    await db_manager.close()


async def _seed_imported_doc(db, title: str = "Test Act 2024", chunks: list[tuple[str, str]] | None = None) -> str:
    """Seed an imported document with chunks. Returns document ID."""
    doc_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()

    await db.execute(
        "INSERT INTO docref_documents "
        "(id, slug, title, latest_version, source_url, csv_url, "
        "chunk_count, status, imported_at, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 'imported', ?, ?, ?)",
        (
            doc_id, "test-act-2024", title, "2024-01-01",
            "https://example.com/test/", "https://example.com/test.csv",
            len(chunks or []), now, now, now,
        ),
    )

    for i, (cid, content) in enumerate(chunks or []):
        await db.execute(
            "INSERT INTO docref_chunks "
            "(id, document_id, chunk_id, url, content, sort_order) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), doc_id, cid, f"https://example.com/#{cid}", content, i),
        )

    await db.commit()
    return doc_id


class TestBuildDocrefContext:
    async def test_empty_ids_returns_empty(self, db) -> None:
        result = await build_docref_context(db, [])
        assert result == ""

    async def test_single_document_context(self, db) -> None:
        doc_id = await _seed_imported_doc(db, chunks=[
            ("s1-title", "Title"),
            ("s1-line1", "This Act is the Test Act 2024."),
        ])
        result = await build_docref_context(db, [doc_id])
        assert "LEGISLATION: Test Act 2024 (2024-01-01)" in result
        assert "[s1-title] Title" in result
        assert "[s1-line1] This Act is the Test Act 2024." in result

    async def test_nonexistent_doc_skipped(self, db) -> None:
        result = await build_docref_context(db, ["nonexistent-id"])
        assert result == ""

    async def test_non_imported_doc_skipped(self, db) -> None:
        doc_id = str(uuid.uuid4())
        now = datetime.now(tz=UTC).isoformat()
        await db.execute(
            "INSERT INTO docref_documents "
            "(id, slug, title, latest_version, source_url, csv_url, "
            "status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'available', ?, ?)",
            (doc_id, "x", "X", "2024-01-01", "https://x/", "https://x.csv", now, now),
        )
        await db.commit()
        result = await build_docref_context(db, [doc_id])
        assert result == ""

    async def test_truncation_with_small_budget(self, db) -> None:
        doc_id = await _seed_imported_doc(db, chunks=[
            ("s1", "A" * 5000),
        ])
        result = await build_docref_context(db, [doc_id], max_tokens=100)
        # 100 tokens * 4 chars = 400 chars max
        assert len(result) <= 400
        assert result.endswith("...")
