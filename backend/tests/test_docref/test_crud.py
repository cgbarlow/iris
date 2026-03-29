"""Integration tests for DocRef extension API routes (ADR-112)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.main import create_app
from app.startup import initialize_databases

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
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
async def client(app_config: AppConfig) -> AsyncIterator[httpx.AsyncClient]:
    application = create_app(app_config)
    db_manager = DatabaseManager(app_config)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as c:
        yield c
    await db_manager.close()


async def _auth_headers(client: httpx.AsyncClient) -> dict[str, str]:
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _install_docref(client: httpx.AsyncClient, headers: dict[str, str]) -> None:
    """Install the docref extension."""
    await client.post(
        "/api/extensions/docref/install",
        json={
            "name": "DocRef",
            "description": "NZ legislation from legislation.docref.nz",
            "version": "1.0.0",
        },
        headers=headers,
    )


async def _seed_test_document(client: httpx.AsyncClient, headers: dict[str, str]) -> str:
    """Insert a test document directly into the database (bypasses external HTTP).

    Returns the document ID.
    """
    import uuid
    from datetime import UTC, datetime

    doc_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()

    # Access the app through the client's transport
    app = client._transport.app  # type: ignore[union-attr]
    db = app.state.db_manager.main_db

    await db.execute(
        "INSERT INTO docref_documents "
        "(id, slug, title, latest_version, source_url, csv_url, "
        "chunk_count, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 0, 'available', ?, ?)",
        (
            doc_id,
            "test-act-2024",
            "Test Act 2024",
            "2024-01-01",
            "https://legislation.docref.nz/test-act-2024/2024-01-01/en/",
            "https://legislation.docref.nz/test-act-2024/2024-01-01/en/test-act-2024-2024-01-01-en-chunked.csv",
            now,
            now,
        ),
    )
    await db.commit()
    return doc_id


class TestDocRefRoutesGating:
    """DocRef routes return 404 when extension is not installed."""

    async def test_documents_404_when_not_installed(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/docref/documents", headers=headers)
        assert resp.status_code == 404

    async def test_refresh_404_when_not_installed(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        resp = await client.post("/api/docref/refresh", headers=headers)
        assert resp.status_code == 404


class TestDocRefListDocuments:
    async def test_empty_list_after_install(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        await _install_docref(client, headers)
        resp = await client.get("/api/docref/documents", headers=headers)
        # May have documents from the post-install refresh or be empty
        # (depending on whether the external fetch succeeded)
        assert resp.status_code == 200
        assert "items" in resp.json()

    async def test_list_seeded_document(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        await _install_docref(client, headers)
        await _seed_test_document(client, headers)
        resp = await client.get("/api/docref/documents", headers=headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        titles = [item["title"] for item in items]
        assert "Test Act 2024" in titles


class TestDocRefDeleteChunks:
    async def test_delete_nonexistent_returns_404(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        await _install_docref(client, headers)
        resp = await client.delete(
            "/api/docref/documents/nonexistent/chunks",
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_delete_chunks_resets_status(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        await _install_docref(client, headers)
        doc_id = await _seed_test_document(client, headers)

        # Manually set to imported with some chunks
        app = client._transport.app  # type: ignore[union-attr]
        db = app.state.db_manager.main_db
        await db.execute(
            "UPDATE docref_documents SET status = 'imported', chunk_count = 5 WHERE id = ?",
            (doc_id,),
        )
        await db.commit()

        resp = await client.delete(
            f"/api/docref/documents/{doc_id}/chunks",
            headers=headers,
        )
        assert resp.status_code == 204

        # Verify status reset
        resp2 = await client.get("/api/docref/documents", headers=headers)
        doc = next(d for d in resp2.json()["items"] if d["id"] == doc_id)
        assert doc["status"] == "available"
        assert doc["chunk_count"] == 0
