"""Schema test for smart_markdown diagram type registration (v6.14.0, ADR-205).

Pairs:
- SQLite  m070_smart_markdown_diagram_type.py
- Supabase m074_smart_markdown_diagram_type.sql

Both seed the diagram_types + diagram_type_notations registry tables
to register ``smart_markdown`` under the existing ``markdown`` notation.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ── SQLite m070 ────────────────────────────────────────────────────────


def test_sqlite_m070_registers_smart_markdown_type() -> None:
    py = _read("app/migrations/m070_smart_markdown_diagram_type.py")
    assert '"smart_markdown"' in py
    assert '"Smart Markdown"' in py
    assert "INSERT OR IGNORE INTO diagram_types" in py


def test_sqlite_m070_maps_to_markdown_notation() -> None:
    py = _read("app/migrations/m070_smart_markdown_diagram_type.py")
    assert "INSERT OR IGNORE INTO diagram_type_notations" in py
    assert '"smart_markdown"' in py
    assert '"markdown"' in py


def test_sqlite_m070_idempotent_via_insert_or_ignore() -> None:
    py = _read("app/migrations/m070_smart_markdown_diagram_type.py")
    assert py.count("INSERT OR IGNORE") >= 2


# ── Supabase m074 ──────────────────────────────────────────────────────


def test_supabase_m074_registers_smart_markdown_type() -> None:
    sql = _read("app/migrations/supabase/m074_smart_markdown_diagram_type.sql")
    assert "INSERT INTO public.diagram_types" in sql
    assert "'smart_markdown'" in sql
    assert "'Smart Markdown'" in sql


def test_supabase_m074_maps_to_markdown_notation() -> None:
    sql = _read("app/migrations/supabase/m074_smart_markdown_diagram_type.sql")
    assert "INSERT INTO public.diagram_type_notations" in sql
    assert "'smart_markdown'" in sql
    assert "'markdown'" in sql


def test_supabase_m074_uses_on_conflict() -> None:
    sql = _read("app/migrations/supabase/m074_smart_markdown_diagram_type.sql")
    # ON CONFLICT DO NOTHING is the Supabase equivalent of SQLite's
    # INSERT OR IGNORE — required by Protocol §15 idempotency.
    assert sql.count("ON CONFLICT") >= 2
    assert "DO NOTHING" in sql


def test_supabase_m074_references_sqlite_mirror() -> None:
    sql = _read("app/migrations/supabase/m074_smart_markdown_diagram_type.sql")
    assert "m070" in sql


def test_supabase_m074_uses_boolean_literal_for_is_default() -> None:
    """Protocol §15: PostgreSQL boolean columns must use TRUE/FALSE."""
    sql = _read("app/migrations/supabase/m074_smart_markdown_diagram_type.sql")
    # FALSE for is_default mapping (smart_markdown isn't the default for
    # the markdown notation — text is).
    assert "FALSE" in sql
