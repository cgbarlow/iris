"""v6.2.0 (ADR-179, SPEC-179-A): artefact store round-trip tests.

Exercises the create + get cycle, mime allowlist, size cap, and
magic-byte validation for pdf / docx.
"""

from __future__ import annotations

import pytest

from app.artefacts import service
from app.artefacts.service import (
    ALLOWED_ARTEFACT_MIMES,
    MAX_ARTEFACT_BYTES,
)


pytestmark = pytest.mark.asyncio


async def _create_table(db) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS artefacts (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            mime TEXT NOT NULL,
            bytes BLOB NOT NULL,
            size_bytes INTEGER NOT NULL,
            source_kind TEXT NOT NULL,
            source_ref TEXT,
            created_by TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """,
    )


async def test_create_then_get_returns_same_bytes(main_db) -> None:
    await _create_table(main_db)
    data = b"# Hello\n"
    meta = await service.create_artefact(
        main_db,
        data=data,
        mime="text/markdown",
        filename="hello-abcd.md",
        source_kind="render_markdown",
        source_ref=None,
        created_by=None,
    )
    assert meta["filename"] == "hello-abcd.md"
    assert meta["mime_type"] == "text/markdown"
    assert meta["size_bytes"] == len(data)
    assert meta["source_kind"] == "render_markdown"

    got = await service.get_artefact(main_db, meta["id"])
    assert got is not None
    assert got["bytes"] == data
    assert got["mime"] == "text/markdown"
    assert got["source_kind"] == "render_markdown"


async def test_get_missing_artefact_returns_none(main_db) -> None:
    await _create_table(main_db)
    got = await service.get_artefact(main_db, "does-not-exist")
    assert got is None


async def test_disallowed_mime_rejected(main_db) -> None:
    await _create_table(main_db)
    with pytest.raises(ValueError, match="not allowed"):
        await service.create_artefact(
            main_db,
            data=b"\x89PNG\r\n\x1a\n",
            mime="image/png",
            filename="x.png",
            source_kind="render_markdown",
        )


async def test_oversized_artefact_rejected(main_db) -> None:
    await _create_table(main_db)
    too_big = b"x" * (MAX_ARTEFACT_BYTES + 1)
    with pytest.raises(ValueError, match="exceeds"):
        await service.create_artefact(
            main_db,
            data=too_big,
            mime="text/markdown",
            filename="big.md",
            source_kind="render_markdown",
        )


async def test_empty_bytes_rejected(main_db) -> None:
    await _create_table(main_db)
    with pytest.raises(ValueError, match="Empty"):
        await service.create_artefact(
            main_db,
            data=b"",
            mime="text/markdown",
            filename="empty.md",
            source_kind="render_markdown",
        )


async def test_pdf_missing_header_rejected(main_db) -> None:
    await _create_table(main_db)
    with pytest.raises(ValueError, match="%PDF header"):
        await service.create_artefact(
            main_db,
            data=b"not a pdf",
            mime="application/pdf",
            filename="x.pdf",
            source_kind="render_markdown",
        )


async def test_docx_missing_zip_sig_rejected(main_db) -> None:
    await _create_table(main_db)
    with pytest.raises(ValueError, match="ZIP signature"):
        await service.create_artefact(
            main_db,
            data=b"not a docx",
            mime=(
                "application/vnd.openxmlformats-"
                "officedocument.wordprocessingml.document"
            ),
            filename="x.docx",
            source_kind="render_markdown",
        )


async def test_pdf_with_valid_header_accepted(main_db) -> None:
    await _create_table(main_db)
    fake_pdf = b"%PDF-1.4 fake but header-valid"
    meta = await service.create_artefact(
        main_db,
        data=fake_pdf,
        mime="application/pdf",
        filename="x-1234.pdf",
        source_kind="render_markdown",
    )
    assert meta["mime_type"] == "application/pdf"


async def test_allowed_mimes_set() -> None:
    assert "text/markdown" in ALLOWED_ARTEFACT_MIMES
    assert (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        in ALLOWED_ARTEFACT_MIMES
    )
    assert "application/pdf" in ALLOWED_ARTEFACT_MIMES
    assert "image/png" not in ALLOWED_ARTEFACT_MIMES
