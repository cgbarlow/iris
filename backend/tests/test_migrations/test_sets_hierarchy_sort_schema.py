"""Schema test for per-set hierarchy sort migration (v6.13.0, ADR-202).

Pairs:
- SQLite  m068_sets_hierarchy_sort.py
- Supabase m072_sets_hierarchy_sort.sql

Both add ``hierarchy_sort TEXT NOT NULL DEFAULT 'manual'`` to ``sets``.
Enum (manual | alpha | newest | oldest) is enforced at the application
layer via Pydantic ``Literal`` rather than a SQL CHECK constraint, so
the SQLite ↔ Supabase syntax stays identical (Protocol §15).

Static-parser style — same shape as
``test_response_format_prompts_schema.py``.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ── SQLite m068 ────────────────────────────────────────────────────────


def test_sqlite_m068_adds_hierarchy_sort_column() -> None:
    py = _read("app/migrations/m068_sets_hierarchy_sort.py")
    assert "ALTER TABLE sets ADD COLUMN hierarchy_sort" in py
    assert "TEXT NOT NULL DEFAULT 'manual'" in py


def test_sqlite_m068_is_idempotent_via_pragma_check() -> None:
    py = _read("app/migrations/m068_sets_hierarchy_sort.py")
    # PRAGMA table_info inspection is the canonical idempotency
    # pattern for SQLite ALTER TABLE (SQLite lacks ADD COLUMN IF NOT EXISTS).
    assert "PRAGMA table_info(sets)" in py
    assert "hierarchy_sort" in py
    assert 'if "hierarchy_sort" not in cols' in py


# ── Supabase m072 ──────────────────────────────────────────────────────


def test_supabase_m072_adds_hierarchy_sort_column() -> None:
    sql = _read("app/migrations/supabase/m072_sets_hierarchy_sort.sql")
    assert "ALTER TABLE public.sets" in sql
    assert "ADD COLUMN IF NOT EXISTS hierarchy_sort" in sql
    assert "TEXT NOT NULL DEFAULT 'manual'" in sql


def test_supabase_m072_is_idempotent() -> None:
    sql = _read("app/migrations/supabase/m072_sets_hierarchy_sort.sql")
    assert "IF NOT EXISTS" in sql


def test_supabase_m072_references_sqlite_mirror() -> None:
    sql = _read("app/migrations/supabase/m072_sets_hierarchy_sort.sql")
    # Protocol §15: pair the Supabase file with its SQLite mirror in
    # the header so reviewers can find them together.
    assert "m068" in sql


def test_supabase_m072_no_boolean_integer_literals() -> None:
    """Protocol §15 regression guard: bare 0/1 in BOOLEAN context."""
    sql = _read("app/migrations/supabase/m072_sets_hierarchy_sort.sql")
    # TEXT column — should not contain `= 0` or `= 1` patterns.
    assert "= 0" not in sql
    assert "= 1" not in sql


# ── Cross-mode consistency ─────────────────────────────────────────────


def test_default_value_matches_across_modes() -> None:
    py = _read("app/migrations/m068_sets_hierarchy_sort.py")
    sql = _read("app/migrations/supabase/m072_sets_hierarchy_sort.sql")
    assert "'manual'" in py
    assert "'manual'" in sql


def test_column_type_matches_across_modes() -> None:
    py = _read("app/migrations/m068_sets_hierarchy_sort.py")
    sql = _read("app/migrations/supabase/m072_sets_hierarchy_sort.sql")
    assert "TEXT NOT NULL" in py
    assert "TEXT NOT NULL" in sql
