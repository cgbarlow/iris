"""Tests for MNEMOS extension gating (ADR-111)."""

import pytest
import pytest_asyncio
import aiosqlite

from app.extensions.service import install_extension, is_extension_enabled


@pytest_asyncio.fixture
async def db():
    async with aiosqlite.connect(":memory:") as conn:
        await conn.executescript("""
            CREATE TABLE extensions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                version TEXT NOT NULL,
                is_enabled INTEGER NOT NULL DEFAULT 1,
                installed_at TEXT NOT NULL,
                installed_by TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                config TEXT DEFAULT '{}'
            );
        """)
        await conn.commit()
        yield conn


@pytest.mark.asyncio
async def test_mnemos_not_installed(db):
    """MNEMOS is not enabled when not installed."""
    assert await is_extension_enabled(db, "mnemos") is False


@pytest.mark.asyncio
async def test_mnemos_installed_and_enabled(db):
    """MNEMOS is enabled when installed with default config."""
    await install_extension(
        db,
        extension_id="mnemos",
        name="MNEMOS",
        description="Semantic retrieval",
        version="1.0.0",
        installed_by="admin",
        config={"url": "http://localhost:8700"},
    )
    assert await is_extension_enabled(db, "mnemos") is True


@pytest.mark.asyncio
async def test_mnemos_installed_but_disabled(db):
    """MNEMOS is not enabled when installed but disabled."""
    await install_extension(
        db,
        extension_id="mnemos",
        name="MNEMOS",
        description="Semantic retrieval",
        version="1.0.0",
        installed_by="admin",
    )
    await db.execute(
        "UPDATE extensions SET is_enabled = 0 WHERE id = ?", ("mnemos",)
    )
    await db.commit()
    assert await is_extension_enabled(db, "mnemos") is False
