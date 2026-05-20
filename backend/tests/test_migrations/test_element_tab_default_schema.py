"""Schema test for per-set element_tab_default migration (v6.16.0, ADR-208).

Pairs:
- SQLite  m072_sets_element_tab_default.py
- Supabase m077_sets_element_tab_default.sql

Both add one TEXT column to ``sets``:
- ``element_tab_default TEXT NOT NULL DEFAULT 'relationships'``

Enum enforced at the Pydantic layer (Protocol §15).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ── SQLite m072 ────────────────────────────────────────────────────────


def test_sqlite_m072_adds_element_tab_default_column() -> None:
    py = _read("app/migrations/m072_sets_element_tab_default.py")
    assert "ALTER TABLE sets ADD COLUMN element_tab_default" in py
    assert "TEXT NOT NULL DEFAULT 'relationships'" in py


def test_sqlite_m072_is_idempotent_via_pragma_check() -> None:
    py = _read("app/migrations/m072_sets_element_tab_default.py")
    assert "PRAGMA table_info(sets)" in py
    assert 'if "element_tab_default" not in cols' in py


# ── Supabase m077 ──────────────────────────────────────────────────────


def test_supabase_m077_adds_element_tab_default_column() -> None:
    sql = _read("app/migrations/supabase/m077_sets_element_tab_default.sql")
    assert "ALTER TABLE public.sets" in sql
    assert "ADD COLUMN IF NOT EXISTS element_tab_default" in sql
    assert "TEXT NOT NULL DEFAULT 'relationships'" in sql


def test_supabase_m077_is_idempotent() -> None:
    sql = _read("app/migrations/supabase/m077_sets_element_tab_default.sql")
    assert "IF NOT EXISTS" in sql


def test_supabase_m077_references_sqlite_mirror() -> None:
    sql = _read("app/migrations/supabase/m077_sets_element_tab_default.sql")
    assert "m072" in sql


def test_supabase_m077_no_boolean_integer_literals() -> None:
    """Protocol §15 regression guard."""
    sql = _read("app/migrations/supabase/m077_sets_element_tab_default.sql")
    assert "= 0" not in sql
    assert "= 1" not in sql


# ── Cross-mode consistency ─────────────────────────────────────────────


def test_defaults_match_across_modes() -> None:
    py = _read("app/migrations/m072_sets_element_tab_default.py")
    sql = _read("app/migrations/supabase/m077_sets_element_tab_default.sql")
    assert "'relationships'" in py
    assert "'relationships'" in sql


def test_column_types_match_across_modes() -> None:
    py = _read("app/migrations/m072_sets_element_tab_default.py")
    sql = _read("app/migrations/supabase/m077_sets_element_tab_default.sql")
    assert "TEXT NOT NULL" in py
    assert "TEXT NOT NULL" in sql
