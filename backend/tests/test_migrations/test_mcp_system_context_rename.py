"""v5.11.0 (ADR-156, SPEC-156-A): static-parser tests asserting that
m050_rename_mcp_prompt_to_mcp_system_context.py and
m054_rename_mcp_prompt_to_mcp_system_context.sql rename the column
on both `collections` and `sets`, with idempotency guards on both
sides of the rename.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_sqlite_m050_renames_collections_column() -> None:
    py = _read("app/migrations/m050_rename_mcp_prompt_to_mcp_system_context.py")
    assert "RENAME COLUMN mcp_prompt TO mcp_system_context" in py


def test_sqlite_m050_handles_both_tables() -> None:
    py = _read("app/migrations/m050_rename_mcp_prompt_to_mcp_system_context.py")
    # Helper is invoked for both collections and sets.
    assert '"collections"' in py
    assert '"sets"' in py


def test_sqlite_m050_is_idempotent() -> None:
    py = _read("app/migrations/m050_rename_mcp_prompt_to_mcp_system_context.py")
    # Guards on both sides: old column must exist, new must not.
    assert '"mcp_prompt" in columns' in py
    assert '"mcp_system_context" not in columns' in py


def test_supabase_m054_renames_both_tables() -> None:
    sql = _read("app/migrations/supabase/m054_rename_mcp_prompt_to_mcp_system_context.sql")
    assert sql.count("RENAME COLUMN mcp_prompt TO mcp_system_context") == 2
    assert "ALTER TABLE public.collections" in sql
    assert "ALTER TABLE public.sets" in sql


def test_supabase_m054_is_idempotent() -> None:
    sql = _read("app/migrations/supabase/m054_rename_mcp_prompt_to_mcp_system_context.sql")
    # information_schema check on both sides of the rename, per table.
    assert sql.count("information_schema.columns") >= 4
    assert "AND NOT EXISTS" in sql
