"""Schema test for per-set tab defaults migration (v6.14.0, ADR-204).

Pairs:
- SQLite  m069_sets_default_tabs.py
- Supabase m073_sets_default_tabs.sql

Both add two TEXT columns to ``sets``:
- ``package_tab_default TEXT NOT NULL DEFAULT 'relationships'``
- ``view_tab_default TEXT NOT NULL DEFAULT 'canvas'``

Enums enforced at the Pydantic layer (Protocol §15).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ── SQLite m069 ────────────────────────────────────────────────────────


def test_sqlite_m069_adds_package_tab_default_column() -> None:
    py = _read("app/migrations/m069_sets_default_tabs.py")
    assert "ALTER TABLE sets ADD COLUMN package_tab_default" in py
    assert "TEXT NOT NULL DEFAULT 'relationships'" in py


def test_sqlite_m069_adds_view_tab_default_column() -> None:
    py = _read("app/migrations/m069_sets_default_tabs.py")
    assert "ALTER TABLE sets ADD COLUMN view_tab_default" in py
    assert "TEXT NOT NULL DEFAULT 'canvas'" in py


def test_sqlite_m069_is_idempotent_via_pragma_check() -> None:
    py = _read("app/migrations/m069_sets_default_tabs.py")
    assert "PRAGMA table_info(sets)" in py
    assert 'if "package_tab_default" not in cols' in py
    assert 'if "view_tab_default" not in cols' in py


# ── Supabase m073 ──────────────────────────────────────────────────────


def test_supabase_m073_adds_package_tab_default_column() -> None:
    sql = _read("app/migrations/supabase/m073_sets_default_tabs.sql")
    assert "ALTER TABLE public.sets" in sql
    assert "ADD COLUMN IF NOT EXISTS package_tab_default" in sql
    assert "TEXT NOT NULL DEFAULT 'relationships'" in sql


def test_supabase_m073_adds_view_tab_default_column() -> None:
    sql = _read("app/migrations/supabase/m073_sets_default_tabs.sql")
    assert "ADD COLUMN IF NOT EXISTS view_tab_default" in sql
    assert "TEXT NOT NULL DEFAULT 'canvas'" in sql


def test_supabase_m073_is_idempotent() -> None:
    sql = _read("app/migrations/supabase/m073_sets_default_tabs.sql")
    # IF NOT EXISTS appears per column.
    assert sql.count("IF NOT EXISTS") >= 2


def test_supabase_m073_references_sqlite_mirror() -> None:
    sql = _read("app/migrations/supabase/m073_sets_default_tabs.sql")
    assert "m069" in sql


def test_supabase_m073_no_boolean_integer_literals() -> None:
    """Protocol §15 regression guard."""
    sql = _read("app/migrations/supabase/m073_sets_default_tabs.sql")
    assert "= 0" not in sql
    assert "= 1" not in sql


# ── Cross-mode consistency ─────────────────────────────────────────────


def test_defaults_match_across_modes() -> None:
    py = _read("app/migrations/m069_sets_default_tabs.py")
    sql = _read("app/migrations/supabase/m073_sets_default_tabs.sql")
    assert "'relationships'" in py
    assert "'relationships'" in sql
    assert "'canvas'" in py
    assert "'canvas'" in sql


def test_column_types_match_across_modes() -> None:
    py = _read("app/migrations/m069_sets_default_tabs.py")
    sql = _read("app/migrations/supabase/m073_sets_default_tabs.sql")
    # TEXT NOT NULL appears for each column in both files.
    assert py.count("TEXT NOT NULL") >= 2
    assert sql.count("TEXT NOT NULL") >= 2
