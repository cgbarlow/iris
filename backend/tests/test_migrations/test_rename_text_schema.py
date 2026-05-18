"""Schema test for the v6.14.1 rename of the 'text' diagram type
display label to 'Standard Markdown' (m071 / m075)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_sqlite_m071_renames_text_to_standard_markdown() -> None:
    py = _read("app/migrations/m071_rename_text_to_standard_markdown.py")
    assert "UPDATE diagram_types SET name = ?" in py
    assert "WHERE id = 'text'" in py
    assert "'Standard Markdown'" in py


def test_supabase_m075_renames_text_to_standard_markdown() -> None:
    sql = _read("app/migrations/supabase/m075_rename_text_to_standard_markdown.sql")
    assert "UPDATE public.diagram_types" in sql
    assert "WHERE id = 'text'" in sql
    assert "'Standard Markdown'" in sql


def test_supabase_m075_references_sqlite_mirror() -> None:
    sql = _read("app/migrations/supabase/m075_rename_text_to_standard_markdown.sql")
    assert "m071" in sql
