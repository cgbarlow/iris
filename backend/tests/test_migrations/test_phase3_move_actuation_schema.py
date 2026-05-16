"""v6.3.0 (ADR-178): static-parser tests for SQLite m062 + Supabase m066
which drop the Phase-1 cross-set move fallback from
`creation-cascade-destination-v1` and replace it with move-tool guidance.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = ROOT.parent


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _read_repo(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


# ── SQLite m062 ────────────────────────────────────────────────────────


def test_sqlite_m062_file_exists() -> None:
    assert (ROOT / "app/migrations/m062_drop_phase1_move_fallback.py").exists()


def test_sqlite_m062_replaces_move_fallback_with_tool_guidance() -> None:
    py = _read("app/migrations/m062_drop_phase1_move_fallback.py")
    # Old fallback hallmark.
    assert "after v6.3.0 ships move_* tools" in py
    # New guidance hallmark.
    assert "move_diagram" in py
    assert "move_package" in py
    assert "REPLACE(" in py


def test_sqlite_m062_scoped_to_destination_prompt() -> None:
    py = _read("app/migrations/m062_drop_phase1_move_fallback.py")
    assert "creation-cascade-destination-v1" in py


def test_sqlite_m062_table_guard() -> None:
    py = _read("app/migrations/m062_drop_phase1_move_fallback.py")
    assert "type='table'" in py


def test_sqlite_m062_registered_in_startup() -> None:
    startup = _read("app/startup.py")
    assert "from app.migrations.m062_drop_phase1_move_fallback import up as m062_up" in startup
    assert "await m062_up(main)" in startup


# ── Supabase m066 ──────────────────────────────────────────────────────


def test_supabase_m066_file_exists() -> None:
    assert (ROOT / "app/migrations/supabase/m066_drop_phase1_move_fallback.sql").exists()


def test_supabase_m066_mirrors_sqlite() -> None:
    sql = _read("app/migrations/supabase/m066_drop_phase1_move_fallback.sql")
    assert "after v6.3.0 ships move_* tools" in sql
    assert "move_diagram" in sql
    assert "REPLACE(" in sql
    assert "creation-cascade-destination-v1" in sql


# ── Seed canonical body ────────────────────────────────────────────────


def test_seed_destination_no_longer_contains_move_fallback() -> None:
    seed = _read("app/seed/creation_prompts.py")
    # The old fallback hallmark gone.
    assert "after v6.3.0 ships move_* tools" not in seed
    # New move-tool guidance present.
    assert "move_diagram" in seed
    assert "move_package" in seed


def test_doc_destination_aligned_with_seed() -> None:
    doc = _read_repo("docs/prompts/creation-cascade-destination.md")
    assert "after v6.3.0 ships move_* tools" not in doc
    assert "move_diagram" in doc
