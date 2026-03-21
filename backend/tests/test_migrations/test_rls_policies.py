"""Tests for m030_rls_policies.sql — ensure every Supabase table has RLS enabled.

This is a structural validation test (the SQLite test environment cannot test
actual PostgreSQL RLS enforcement). It parses the migration SQL and verifies
that every table created by m001–m029 has a corresponding
ALTER TABLE ... ENABLE ROW LEVEL SECURITY statement in m030.
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

_RLS_FILE = os.path.join(_MIGRATIONS_DIR, "m030_rls_policies.sql")


def _get_created_tables() -> set[str]:
    """Parse all m001–m029 .sql files and extract table names from CREATE TABLE."""
    tables: set[str] = set()
    for filename in sorted(os.listdir(_MIGRATIONS_DIR)):
        if not filename.endswith(".sql"):
            continue
        # Only include m001 through m029 (exclude m030+ which is the RLS file itself)
        match = re.match(r"m(\d+)", filename)
        if not match:
            continue
        num = int(match.group(1))
        if num >= 30:
            continue
        filepath = os.path.join(_MIGRATIONS_DIR, filename)
        with open(filepath) as f:
            content = f.read()
        for m in re.finditer(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)",
            content,
            re.IGNORECASE,
        ):
            tables.add(m.group(1))
    return tables


def _get_rls_tables() -> set[str]:
    """Parse m030_rls_policies.sql and extract table names from ALTER TABLE ... ENABLE ROW LEVEL SECURITY."""
    with open(_RLS_FILE) as f:
        content = f.read()
    tables: set[str] = set()
    for m in re.finditer(
        r"ALTER\s+TABLE\s+(\w+)\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY",
        content,
        re.IGNORECASE,
    ):
        tables.add(m.group(1))
    return tables


def test_rls_migration_file_exists() -> None:
    """m030_rls_policies.sql must exist in the Supabase migrations directory."""
    assert os.path.isfile(_RLS_FILE), f"Missing: {_RLS_FILE}"


def test_every_table_has_rls() -> None:
    """Every table created by m001–m029 must have RLS enabled in m030."""
    created = _get_created_tables()
    rls = _get_rls_tables()

    missing = created - rls
    assert not missing, (
        f"Tables missing RLS in m030_rls_policies.sql: {sorted(missing)}"
    )


def test_no_extra_rls_tables() -> None:
    """m030 should not enable RLS on tables that don't exist in m001–m029."""
    created = _get_created_tables()
    rls = _get_rls_tables()

    extra = rls - created
    assert not extra, (
        f"RLS enabled on tables not created by m001–m029: {sorted(extra)}"
    )
