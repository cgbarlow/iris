"""v6.2.0 (ADR-179): static-parser tests for SQLite m061 + Supabase m065
which drop the Phase-1 docx/pdf fallback from
`creation-cascade-destination-v1` and replace it with renderer-call
guidance. The cross-set move fallback stays (drops in Phase 3 / v6.3.0).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = ROOT.parent


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _read_repo(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


# ── SQLite m061 ────────────────────────────────────────────────────────


def test_sqlite_m061_file_exists() -> None:
    assert (ROOT / "app/migrations/m061_drop_phase1_docx_fallback.py").exists()


def test_sqlite_m061_replaces_docx_fallback_with_renderer_guidance() -> None:
    py = _read("app/migrations/m061_drop_phase1_docx_fallback.py")
    # Old fallback string the migration is removing.
    assert "Docx and PDF generation ships in" in py
    # New guidance string the migration writes.
    assert "render_markdown" in py
    assert "REPLACE(" in py


def test_sqlite_m061_scoped_to_destination_prompt_only() -> None:
    py = _read("app/migrations/m061_drop_phase1_docx_fallback.py")
    assert "creation-cascade-destination-v1" in py


def test_sqlite_m061_table_guard() -> None:
    py = _read("app/migrations/m061_drop_phase1_docx_fallback.py")
    assert "type='table'" in py
    assert "ai_creation_prompts" in py


def test_sqlite_m061_registered_in_startup() -> None:
    startup = _read("app/startup.py")
    assert "from app.migrations.m061_drop_phase1_docx_fallback import up as m061_up" in startup
    assert "await m061_up(main)" in startup


# ── Supabase m065 ──────────────────────────────────────────────────────


def test_supabase_m065_file_exists() -> None:
    assert (ROOT / "app/migrations/supabase/m065_drop_phase1_docx_fallback.sql").exists()


def test_supabase_m065_replaces_same_strings() -> None:
    sql = _read("app/migrations/supabase/m065_drop_phase1_docx_fallback.sql")
    assert "Docx and PDF generation ships in" in sql
    assert "render_markdown" in sql
    assert "REPLACE(" in sql
    assert "creation-cascade-destination-v1" in sql


# ── Seed canonical body alignment ──────────────────────────────────────


def test_seed_destination_body_no_longer_contains_docx_fallback() -> None:
    seed = _read("app/seed/creation_prompts.py")
    # The exact old fallback line should be gone.
    assert "Docx and PDF generation ships in" not in seed
    # The new renderer-call guidance is present.
    assert "render_markdown" in seed


def test_seed_destination_body_drops_move_fallback_after_phase3() -> None:
    """Phase 2 (v6.2.0) only dropped the docx/pdf fallback; Phase 3
    (v6.3.0) drops the cross-set move fallback too. After Phase 3
    lands the seed no longer contains either fallback string.
    """
    seed = _read("app/seed/creation_prompts.py")
    # Move fallback gone after Phase 3.
    assert "v6.3.0 ships move_* tools" not in seed
    # Move-tool guidance present instead.
    assert "move_diagram" in seed


def test_doc_destination_body_aligned_with_seed() -> None:
    """The canonical paste-ready doc must match the seed canonical body
    so admins reading the doc see the same content the seed re-applies."""
    doc = _read_repo("docs/prompts/creation-cascade-destination.md")
    assert "Docx and PDF generation ships in" not in doc
    assert "render_markdown" in doc
    # After Phase 3 the move-tools guidance replaces the v6.3.0
    # promise text — assert the move tools are mentioned (Phase 3
    # actuation), not the placeholder.
    assert "move_diagram" in doc
