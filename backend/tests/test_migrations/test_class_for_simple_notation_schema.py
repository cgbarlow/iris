"""v6.7.4 (ADR-188, issue #160): static-parser tests asserting that
SQLite m066 and Supabase m070 register the (class, simple) pair in
diagram_type_notations.

Element 09158b60-94cd-46db-9211-a4d50c9c1550 in the UAT dataset has
notation='simple' and element_type='class' — the registry was out of
step with live data, hiding 'class' from the simple-notation dropdown.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ── SQLite m066 ─────────────────────────────────────────────────────────


def test_sqlite_m066_inserts_class_simple_pair() -> None:
    py = _read("app/migrations/m066_class_for_simple_notation.py")
    assert "INSERT OR IGNORE INTO diagram_type_notations" in py
    assert '("class", "simple", 0)' in py


def test_sqlite_m066_is_idempotent() -> None:
    py = _read("app/migrations/m066_class_for_simple_notation.py")
    # INSERT OR IGNORE is the SQLite idempotency marker.
    assert "INSERT OR IGNORE" in py


def test_sqlite_m066_has_migration_id() -> None:
    py = _read("app/migrations/m066_class_for_simple_notation.py")
    assert 'MIGRATION_ID = "m066_class_for_simple_notation"' in py


# ── Supabase m070 ───────────────────────────────────────────────────────


def test_supabase_m070_inserts_class_simple_pair() -> None:
    sql = _read("app/migrations/supabase/m070_class_for_simple_notation.sql")
    assert "INSERT INTO public.diagram_type_notations" in sql
    assert "'class', 'simple'" in sql


def test_supabase_m070_uses_boolean_literal_for_is_default() -> None:
    """Protocol §15: `is_default` is BOOLEAN on Postgres. The new mapping
    must use `FALSE` (boolean), not `0` (integer). This is the same
    regression guard pattern as test_response_format_prompts_schema.py.
    """
    sql = _read("app/migrations/supabase/m070_class_for_simple_notation.sql")
    assert "VALUES ('class', 'simple', FALSE)" in sql, (
        "is_default must be `FALSE` (boolean), not `0` (integer), on "
        "the Postgres-backed Supabase schema."
    )
    # Ensure no integer literal slipped in by accident.
    assert "VALUES ('class', 'simple', 0)" not in sql
    assert "VALUES ('class', 'simple', 1)" not in sql


def test_supabase_m070_is_idempotent() -> None:
    sql = _read("app/migrations/supabase/m070_class_for_simple_notation.sql")
    assert "ON CONFLICT (diagram_type_id, notation_id) DO NOTHING" in sql


def test_supabase_m070_documents_pairing() -> None:
    sql = _read("app/migrations/supabase/m070_class_for_simple_notation.sql")
    # Protocol §15: link Supabase file to its SQLite mirror in the header.
    assert "Mirrors SQLite m066" in sql
