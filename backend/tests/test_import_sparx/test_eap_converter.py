"""Tests for EAP (JET4/MDB) to SQLite converter."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

import aiosqlite
import pytest

from app.import_sparx.eap_converter import (
    REQUIRED_TABLES,
    convert_eap_to_sqlite,
    is_jet4_file,
)

# Path to the sample .qea file (SQLite format, not JET4)
SAMPLE_QEA = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "docs", "reference", "SparxEA", "AIXM_5.1.1_EA16.qea",
)
SAMPLE_QEA = os.path.abspath(SAMPLE_QEA)

# Path to a sample .eap file if available
SAMPLE_EAP_DIR = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "docs", "reference", "SparxEA",
)
SAMPLE_EAP_DIR = os.path.abspath(SAMPLE_EAP_DIR)


def _find_sample_eap() -> str | None:
    """Find a sample .eap file in the reference directory."""
    if os.path.isdir(SAMPLE_EAP_DIR):
        for f in os.listdir(SAMPLE_EAP_DIR):
            if f.endswith(".eap"):
                return os.path.join(SAMPLE_EAP_DIR, f)
    return None


def _create_jet4_file() -> str:
    """Create a minimal file with JET4 magic header."""
    tmp = tempfile.NamedTemporaryFile(suffix=".eap", delete=False)
    # JET4 signature: \x00\x01\x00\x00Standard Jet DB + padding
    header = b"\x00\x01\x00\x00Standard Jet DB" + b"\x00" * 4077
    tmp.write(header)
    tmp.close()
    return tmp.name


# ---------- is_jet4_file Tests ----------


class TestIsJet4File:
    """Verify JET4 header detection."""

    def test_is_jet4_file_valid(self) -> None:
        path = _create_jet4_file()
        try:
            assert is_jet4_file(path) is True
        finally:
            os.unlink(path)

    def test_is_jet4_file_sqlite(self) -> None:
        """SQLite files should not be detected as JET4."""
        assert is_jet4_file(SAMPLE_QEA) is False

    def test_is_jet4_file_empty(self) -> None:
        tmp = tempfile.NamedTemporaryFile(suffix=".eap", delete=False)
        tmp.close()
        try:
            assert is_jet4_file(tmp.name) is False
        finally:
            os.unlink(tmp.name)

    def test_is_jet4_file_nonexistent(self) -> None:
        assert is_jet4_file("/nonexistent/path.eap") is False


# ---------- convert_eap_to_sqlite Tests ----------


class TestConvertEapToSqlite:
    """Verify MDB→SQLite conversion."""

    async def test_convert_raises_without_mdbtools(self) -> None:
        with patch("app.import_sparx.eap_converter.shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="mdbtools is not installed"):
                await convert_eap_to_sqlite("/some/file.eap")

    async def test_convert_raises_for_non_jet4(self) -> None:
        """SQLite files should be rejected."""
        with pytest.raises(ValueError, match="not a JET4"):
            await convert_eap_to_sqlite(SAMPLE_QEA)

    @pytest.mark.skipif(
        _find_sample_eap() is None,
        reason="No sample .eap file in docs/reference/SparxEA/",
    )
    async def test_convert_produces_valid_sqlite(self) -> None:
        eap_path = _find_sample_eap()
        assert eap_path is not None
        sqlite_path = await convert_eap_to_sqlite(eap_path)
        try:
            async with aiosqlite.connect(sqlite_path) as db:
                cursor = await db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                tables = {row[0] for row in await cursor.fetchall()}
                # At least some of the required tables should exist
                found = tables & set(REQUIRED_TABLES)
                assert len(found) >= 4, f"Expected >=4 tables, found: {found}"
        finally:
            os.unlink(sqlite_path)

    @pytest.mark.skipif(
        _find_sample_eap() is None,
        reason="No sample .eap file in docs/reference/SparxEA/",
    )
    async def test_converted_tables_have_expected_columns(self) -> None:
        """Verify converted tables have columns matching reader.py queries."""
        eap_path = _find_sample_eap()
        assert eap_path is not None
        sqlite_path = await convert_eap_to_sqlite(eap_path)
        try:
            async with aiosqlite.connect(sqlite_path) as db:
                # Check t_package columns
                cursor = await db.execute("PRAGMA table_info(t_package)")
                cols = {row[1] for row in await cursor.fetchall()}
                assert "Package_ID" in cols
                assert "Name" in cols
                assert "Parent_ID" in cols

                # Check t_object columns
                cursor = await db.execute("PRAGMA table_info(t_object)")
                cols = {row[1] for row in await cursor.fetchall()}
                assert "Object_ID" in cols
                assert "Object_Type" in cols
                assert "Name" in cols
                assert "Package_ID" in cols

                # Check t_connector columns
                cursor = await db.execute("PRAGMA table_info(t_connector)")
                cols = {row[1] for row in await cursor.fetchall()}
                assert "Connector_ID" in cols
                assert "Connector_Type" in cols
                assert "Start_Object_ID" in cols
                assert "End_Object_ID" in cols
        finally:
            os.unlink(sqlite_path)
