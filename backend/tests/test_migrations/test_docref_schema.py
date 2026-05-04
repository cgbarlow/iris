"""Tests for m043_docref_tables.sql — Postgres parity for the DocRef extension.

The DocRef extension's tables (docref_documents, docref_chunks) are created
on SQLite by the Python migration m034_docref_tables.py. This test enforces
that an equivalent Supabase SQL migration exists so the Legislation feature
works on Postgres deployments (issue #24, ADR-135).

Structural validation only — the SQLite test environment cannot run real
Postgres. The test parses the migration SQL and verifies the tables, the
columns required by the service layer, the indexes, and that RLS is enabled.
"""

from __future__ import annotations

import os
import re

import pytest

_MIGRATIONS_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "app",
    "migrations",
    "supabase",
)

_DOCREF_FILE = os.path.join(_MIGRATIONS_DIR, "m043_docref_tables.sql")


# Columns the service layer (backend/app/docref/service.py) reads in _SELECT
# and writes in INSERT/UPDATE statements. If any are missing the API breaks.
_DOCUMENTS_COLUMNS = {
    "id",
    "slug",
    "title",
    "latest_version",
    "source_url",
    "csv_url",
    "chunk_count",
    "status",
    "error_message",
    "imported_at",
    "imported_by",
    "created_at",
    "updated_at",
}

_CHUNKS_COLUMNS = {
    "id",
    "document_id",
    "chunk_id",
    "url",
    "content",
    "sort_order",
}


def _read_sql() -> str:
    with open(_DOCREF_FILE) as f:
        return f.read()


def _columns_in_create(sql: str, table: str) -> set[str]:
    """Extract column names from a CREATE TABLE block."""
    match = re.search(
        rf"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?{re.escape(table)}\s*\((.+?)\)\s*;",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return set()
    body = match.group(1)
    columns: set[str] = set()
    # First token on each comma-separated line that is not a constraint keyword
    for raw in re.split(r",(?![^()]*\))", body):
        token = raw.strip().split()
        if not token:
            continue
        head = token[0].upper()
        if head in {
            "CONSTRAINT",
            "PRIMARY",
            "FOREIGN",
            "UNIQUE",
            "CHECK",
        }:
            continue
        columns.add(token[0].strip('"').lower())
    return columns


def test_docref_migration_file_exists() -> None:
    """m043_docref_tables.sql must exist in the Supabase migrations directory."""
    assert os.path.isfile(_DOCREF_FILE), (
        f"Missing: {_DOCREF_FILE}. "
        "DocRef Legislation feature will fail on Supabase deployments."
    )


def test_creates_docref_documents_table() -> None:
    sql = _read_sql()
    assert re.search(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?docref_documents\s*\(",
        sql,
        re.IGNORECASE,
    ), "m043 must create the docref_documents table."


def test_creates_docref_chunks_table() -> None:
    sql = _read_sql()
    assert re.search(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?docref_chunks\s*\(",
        sql,
        re.IGNORECASE,
    ), "m043 must create the docref_chunks table."


def test_docref_documents_has_all_service_columns() -> None:
    sql = _read_sql()
    cols = _columns_in_create(sql, "docref_documents")
    missing = _DOCUMENTS_COLUMNS - cols
    assert not missing, (
        f"docref_documents missing columns required by service.py: {sorted(missing)}"
    )


def test_docref_chunks_has_all_service_columns() -> None:
    sql = _read_sql()
    cols = _columns_in_create(sql, "docref_chunks")
    missing = _CHUNKS_COLUMNS - cols
    assert not missing, (
        f"docref_chunks missing columns required by service.py: {sorted(missing)}"
    )


def test_docref_chunks_references_documents() -> None:
    """Cascade delete from documents to chunks must be preserved (matches SQLite m034)."""
    sql = _read_sql()
    assert re.search(
        r"document_id[^,]*REFERENCES\s+docref_documents\s*\(\s*id\s*\)[^,]*ON\s+DELETE\s+CASCADE",
        sql,
        re.IGNORECASE | re.DOTALL,
    ), "docref_chunks.document_id must REFERENCE docref_documents(id) ON DELETE CASCADE."


def test_unique_constraint_on_documents_slug_version() -> None:
    sql = _read_sql()
    assert re.search(
        r"UNIQUE\s*\(\s*slug\s*,\s*latest_version\s*\)",
        sql,
        re.IGNORECASE,
    ), "docref_documents must have UNIQUE(slug, latest_version) — matches SQLite m034."


def test_unique_constraint_on_chunks_document_chunk_id() -> None:
    sql = _read_sql()
    assert re.search(
        r"UNIQUE\s*\(\s*document_id\s*,\s*chunk_id\s*\)",
        sql,
        re.IGNORECASE,
    ), "docref_chunks must have UNIQUE(document_id, chunk_id) — matches SQLite m034."


@pytest.mark.parametrize(
    "index_name,table,column",
    [
        ("idx_docref_documents_slug", "docref_documents", "slug"),
        ("idx_docref_documents_status", "docref_documents", "status"),
        ("idx_docref_chunks_document_id", "docref_chunks", "document_id"),
    ],
)
def test_indexes_present(index_name: str, table: str, column: str) -> None:
    sql = _read_sql()
    assert re.search(
        rf"CREATE\s+INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?{re.escape(index_name)}\s+ON\s+{re.escape(table)}\s*\(\s*{re.escape(column)}",
        sql,
        re.IGNORECASE,
    ), f"Missing index {index_name} on {table}({column})."


@pytest.mark.parametrize("table", ["docref_documents", "docref_chunks"])
def test_rls_enabled(table: str) -> None:
    """Every Supabase table must have RLS enabled (m030 invariant for new tables)."""
    sql = _read_sql()
    assert re.search(
        rf"ALTER\s+TABLE\s+{re.escape(table)}\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY",
        sql,
        re.IGNORECASE,
    ), f"{table} must have RLS enabled in m043."
