"""v5.8.0 (ADR-150, SPEC-150-A): static-parser test asserting the
Supabase migration `m051_scope_system_prompts.sql` mirrors the SQLite
migration `m047_scope_system_prompts.py`."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_sqlite_m047_adds_collections_system_prompt() -> None:
    py = _read("app/migrations/m047_scope_system_prompts.py")
    assert "ALTER TABLE collections ADD COLUMN system_prompt" in py


def test_sqlite_m047_adds_sets_system_prompt() -> None:
    py = _read("app/migrations/m047_scope_system_prompts.py")
    assert "ALTER TABLE sets ADD COLUMN system_prompt" in py


def test_sqlite_m047_is_idempotent_on_collections() -> None:
    py = _read("app/migrations/m047_scope_system_prompts.py")
    # Idempotency guard: PRAGMA table_info inspection before ALTER.
    assert "PRAGMA table_info(collections)" in py


def test_sqlite_m047_is_idempotent_on_sets() -> None:
    py = _read("app/migrations/m047_scope_system_prompts.py")
    assert "PRAGMA table_info(sets)" in py


def test_supabase_m051_adds_collections_system_prompt() -> None:
    sql = _read("app/migrations/supabase/m051_scope_system_prompts.sql")
    assert "ALTER TABLE collections" in sql
    assert "ADD COLUMN IF NOT EXISTS system_prompt" in sql


def test_supabase_m051_adds_sets_system_prompt() -> None:
    sql = _read("app/migrations/supabase/m051_scope_system_prompts.sql")
    assert "ALTER TABLE sets" in sql
    # Both ALTERs add system_prompt; verify the column appears at least twice
    # (once per table). Substring count is sufficient — the SQL file has
    # no other reason to mention system_prompt.
    assert sql.count("system_prompt") >= 2
