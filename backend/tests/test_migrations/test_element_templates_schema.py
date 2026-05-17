"""v6.8.0 (ADR-191, issue #153): static-parser tests asserting that
SQLite m067 and Supabase m071 create the ``element_templates`` table
with the expected columns, indexes, and scoping consistency CHECK
constraint.

Pattern follows test_response_format_prompts_schema.py /
test_cascade_ux_polish_schema.py — readonly file inspection, no DB
spin-up.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ── SQLite m067 ─────────────────────────────────────────────────────────


def test_sqlite_m067_creates_element_templates_table() -> None:
    py = _read("app/migrations/m067_element_templates.py")
    assert "CREATE TABLE IF NOT EXISTS element_templates" in py


def test_sqlite_m067_has_required_columns() -> None:
    py = _read("app/migrations/m067_element_templates.py")
    for col in (
        "id TEXT PRIMARY KEY",
        "name TEXT NOT NULL",
        "set_id TEXT REFERENCES sets(id)",
        "is_global INTEGER NOT NULL DEFAULT 0",
        "source_element_id TEXT REFERENCES elements(id)",
        "included_fields TEXT NOT NULL",
        "template_data TEXT NOT NULL",
        "is_deleted INTEGER NOT NULL DEFAULT 0",
    ):
        assert col in py, f"missing column declaration: {col!r}"


def test_sqlite_m067_enforces_scoping_check_constraint() -> None:
    py = _read("app/migrations/m067_element_templates.py")
    # The CHECK constraint guarantees set_id ↔ is_global consistency.
    assert "CHECK" in py
    assert "(is_global = 1 AND set_id IS NULL)" in py
    assert "(is_global = 0 AND set_id IS NOT NULL)" in py


def test_sqlite_m067_creates_indexes() -> None:
    py = _read("app/migrations/m067_element_templates.py")
    assert "CREATE INDEX IF NOT EXISTS idx_element_templates_set" in py
    assert "CREATE INDEX IF NOT EXISTS idx_element_templates_global" in py


def test_sqlite_m067_is_idempotent() -> None:
    py = _read("app/migrations/m067_element_templates.py")
    assert "CREATE TABLE IF NOT EXISTS" in py
    assert "CREATE INDEX IF NOT EXISTS" in py


def test_sqlite_m067_has_migration_id() -> None:
    py = _read("app/migrations/m067_element_templates.py")
    assert 'MIGRATION_ID = "m067_element_templates"' in py


# ── Supabase m071 ───────────────────────────────────────────────────────


def test_supabase_m071_creates_element_templates_table() -> None:
    sql = _read("app/migrations/supabase/m071_element_templates.sql")
    assert "CREATE TABLE IF NOT EXISTS public.element_templates" in sql


def test_supabase_m071_uses_boolean_literals_for_is_global() -> None:
    """Protocol §15: BOOLEAN columns on Postgres must use TRUE/FALSE
    literals, not 0/1. is_global and is_deleted are both BOOLEAN
    here. Regression guard pattern from
    test_response_format_prompts_schema.py.
    """
    sql = _read("app/migrations/supabase/m071_element_templates.sql")
    # Column declarations
    assert "is_global BOOLEAN NOT NULL DEFAULT FALSE" in sql
    assert "is_deleted BOOLEAN NOT NULL DEFAULT FALSE" in sql
    # CHECK constraint references
    assert "is_global = TRUE" in sql
    assert "is_global = FALSE" in sql
    # No integer-literal slip-ups
    assert "is_global = 1" not in sql
    assert "is_global = 0" not in sql
    assert "is_global INTEGER" not in sql


def test_supabase_m071_check_constraint_uses_boolean_literals() -> None:
    sql = _read("app/migrations/supabase/m071_element_templates.sql")
    assert (
        "CONSTRAINT element_templates_scoping_consistent CHECK ("
        in sql
    )
    assert "(is_global = TRUE AND set_id IS NULL)" in sql
    assert "(is_global = FALSE AND set_id IS NOT NULL)" in sql


def test_supabase_m071_creates_indexes_with_boolean_predicate() -> None:
    sql = _read("app/migrations/supabase/m071_element_templates.sql")
    assert "idx_element_templates_set" in sql
    assert "WHERE is_deleted = FALSE" in sql
    assert "idx_element_templates_global" in sql


def test_supabase_m071_is_idempotent() -> None:
    sql = _read("app/migrations/supabase/m071_element_templates.sql")
    assert sql.count("CREATE TABLE IF NOT EXISTS") >= 1
    assert sql.count("CREATE INDEX IF NOT EXISTS") >= 2


def test_supabase_m071_documents_pairing() -> None:
    sql = _read("app/migrations/supabase/m071_element_templates.sql")
    assert "Mirrors SQLite m067" in sql
