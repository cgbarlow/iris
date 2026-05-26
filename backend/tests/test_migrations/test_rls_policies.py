"""Structural validation for Supabase RLS coverage (ADR-095).

The SQLite test environment cannot exercise PostgreSQL RLS enforcement,
so these tests parse the migration SQL instead. They verify that every
table created by any Supabase migration has a corresponding
``ALTER TABLE ... ENABLE ROW LEVEL SECURITY`` statement somewhere in the
migration set.

History: the original sweep landed in m030 covering m001–m029. Later
migrations enable RLS in the same file that creates the table. Issue
#236 surfaced three tables (artefacts, element_templates,
aggregation_profiles) that slipped through; m085 backfills them and
this test now scans the full migration tree so future drift is caught
in CI.
"""

from __future__ import annotations

import os
import re

_MIGRATIONS_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "app",
    "migrations",
    "supabase",
)

_RLS_FILE = os.path.join(_MIGRATIONS_DIR, "m030_rls_policies.sql")


def _migration_files() -> list[str]:
    return sorted(
        os.path.join(_MIGRATIONS_DIR, fn)
        for fn in os.listdir(_MIGRATIONS_DIR)
        if fn.endswith(".sql")
    )


def _get_created_tables(max_migration: int | None = None) -> set[str]:
    """Extract table names from CREATE TABLE statements across migrations.

    ``max_migration`` (exclusive) limits the scan — used by the legacy
    m001–m029 check. Strips an optional ``public.`` schema prefix so
    tables created with and without it compare equal.
    """
    tables: set[str] = set()
    for filepath in _migration_files():
        filename = os.path.basename(filepath)
        match = re.match(r"m(\d+)", filename)
        if not match:
            continue
        num = int(match.group(1))
        if max_migration is not None and num >= max_migration:
            continue
        with open(filepath) as f:
            content = f.read()
        for m in re.finditer(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:public\.)?(\w+)",
            content,
            re.IGNORECASE,
        ):
            tables.add(m.group(1))
    return tables


def _get_rls_tables(file: str | None = None) -> set[str]:
    """Extract table names from ENABLE ROW LEVEL SECURITY statements.

    If ``file`` is given, scan only that file (legacy m030 check).
    Otherwise scan every Supabase migration.
    """
    files = [file] if file else _migration_files()
    tables: set[str] = set()
    for filepath in files:
        with open(filepath) as f:
            content = f.read()
        for m in re.finditer(
            r"ALTER\s+TABLE\s+(?:public\.)?(\w+)\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY",
            content,
            re.IGNORECASE,
        ):
            tables.add(m.group(1))
    return tables


def test_rls_migration_file_exists() -> None:
    """m030_rls_policies.sql must exist in the Supabase migrations directory."""
    assert os.path.isfile(_RLS_FILE), f"Missing: {_RLS_FILE}"


def test_every_m001_m029_table_has_rls_in_m030() -> None:
    """Every table created by m001–m029 must have RLS enabled in m030."""
    created = _get_created_tables(max_migration=30)
    rls = _get_rls_tables(file=_RLS_FILE)

    missing = created - rls
    assert not missing, (
        f"Tables missing RLS in m030_rls_policies.sql: {sorted(missing)}"
    )


def test_every_supabase_table_has_rls_enabled() -> None:
    """Every table created by any Supabase migration must have RLS enabled
    somewhere in the migration set (ADR-095)."""
    created = _get_created_tables()
    rls = _get_rls_tables()

    missing = created - rls
    assert not missing, (
        "Supabase tables missing ENABLE ROW LEVEL SECURITY anywhere in "
        f"the migration set: {sorted(missing)}. Add the ALTER TABLE in "
        "the same migration that creates the table, or in a follow-up "
        "RLS-fix migration like m085."
    )
