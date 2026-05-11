"""v5.10.0 (ADR-155, SPEC-155-A): static-parser tests asserting that
m049_mcp_prompt_column.py and m053_mcp_prompt_and_prompts_timestamps.sql
add `mcp_prompt` to `collections` + `sets`, and that the Supabase
mirror also fixes the v5.9.0 `prompts.created_at` / `updated_at`
column types to timestamptz.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_sqlite_m049_adds_collections_mcp_prompt() -> None:
    py = _read("app/migrations/m049_mcp_prompt_column.py")
    assert "ALTER TABLE collections ADD COLUMN mcp_prompt" in py


def test_sqlite_m049_adds_sets_mcp_prompt() -> None:
    py = _read("app/migrations/m049_mcp_prompt_column.py")
    assert "ALTER TABLE sets ADD COLUMN mcp_prompt" in py


def test_sqlite_m049_is_idempotent() -> None:
    py = _read("app/migrations/m049_mcp_prompt_column.py")
    # PRAGMA table_info inspection before ALTER on both tables.
    assert py.count("PRAGMA table_info") >= 2


def test_supabase_m053_adds_mcp_prompt_columns() -> None:
    sql = _read("app/migrations/supabase/m053_mcp_prompt_and_prompts_timestamps.sql")
    assert "ALTER TABLE collections" in sql
    assert "ALTER TABLE sets" in sql
    assert "ADD COLUMN IF NOT EXISTS mcp_prompt TEXT" in sql
    # Both tables get the column — substring count >= 2.
    assert sql.count("mcp_prompt") >= 2


def test_supabase_m053_fixes_prompts_timestamps() -> None:
    sql = _read("app/migrations/supabase/m053_mcp_prompt_and_prompts_timestamps.sql")
    # Convert created_at + updated_at to timestamptz on the v5.9.0 prompts table.
    assert "ALTER COLUMN created_at TYPE timestamptz" in sql
    assert "ALTER COLUMN updated_at TYPE timestamptz" in sql
    # Guarded so re-running on an already-fixed DB is a no-op.
    assert "data_type = 'text'" in sql
