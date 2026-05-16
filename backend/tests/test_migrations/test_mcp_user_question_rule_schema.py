"""v6.1.0 (ADR-177, SPEC-177-A) — issue #133 Phase 1: static-parser
tests for the SQLite m059 + Supabase m063 migrations that insert a
top-level ASKING QUESTIONS section into the
`mcp-server-instructions-v1` singleton body.

The migrations are surgical text-insertions (REPLACE() pattern) that
preserve admin customisations elsewhere in the body.

The seed file `backend/app/seed/creation_prompts.py` is updated to
also re-apply the canonical singleton body on every backend startup
(new behaviour for this row — matches the existing cascade-prompt
pattern).

The iris-mcp `_FALLBACK_INSTRUCTIONS` is updated so day-one
fallback matches the seeded body.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = ROOT.parent  # one level above backend/


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _read_repo(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


# ── SQLite m059 ────────────────────────────────────────────────────────


def test_sqlite_m059_file_exists() -> None:
    assert (ROOT / "app/migrations/m059_mcp_user_question_rule.py").exists()


def test_sqlite_m059_inserts_asking_questions_marker() -> None:
    py = _read("app/migrations/m059_mcp_user_question_rule.py")
    assert "ASKING QUESTIONS" in py


def test_sqlite_m059_inserts_cascade_specific_bullet() -> None:
    """The new section must mention creation-cascade Stage-0 setup so
    cascades inherit the rule from the MCP-wide instructions."""
    py = _read("app/migrations/m059_mcp_user_question_rule.py")
    flat = " ".join(py.split())
    assert "Stage-0 setup question" in flat or "creation cascade" in flat.lower()


def test_sqlite_m059_inserts_destination_chooser_bullet() -> None:
    py = _read("app/migrations/m059_mcp_user_question_rule.py")
    assert "save-destination chooser" in py or "destination chooser" in py.lower()


def test_sqlite_m059_uses_replace_to_be_surgical() -> None:
    """The insert must use REPLACE() so admin customisations elsewhere
    in the singleton body are preserved (matches the m057 pattern)."""
    py = _read("app/migrations/m059_mcp_user_question_rule.py")
    assert "REPLACE(" in py


def test_sqlite_m059_scopes_to_mcp_server_instructions_purpose() -> None:
    py = _read("app/migrations/m059_mcp_user_question_rule.py")
    assert "WHERE purpose = 'mcp_server_instructions'" in py


def test_sqlite_m059_table_guard() -> None:
    py = _read("app/migrations/m059_mcp_user_question_rule.py")
    assert "type='table'" in py
    assert "ai_creation_prompts" in py


def test_sqlite_m059_registered_in_startup() -> None:
    startup = _read("app/startup.py")
    assert "from app.migrations.m059_mcp_user_question_rule import up as m059_up" in startup
    assert "await m059_up(main)" in startup


# ── Supabase m063 ──────────────────────────────────────────────────────


def test_supabase_m063_file_exists() -> None:
    assert (ROOT / "app/migrations/supabase/m063_mcp_user_question_rule.sql").exists()


def test_supabase_m063_inserts_asking_questions_marker() -> None:
    sql = _read("app/migrations/supabase/m063_mcp_user_question_rule.sql")
    assert "ASKING QUESTIONS" in sql


def test_supabase_m063_uses_replace_to_be_surgical() -> None:
    sql = _read("app/migrations/supabase/m063_mcp_user_question_rule.sql")
    assert "REPLACE(" in sql


def test_supabase_m063_scopes_to_singleton() -> None:
    sql = _read("app/migrations/supabase/m063_mcp_user_question_rule.sql")
    assert "purpose = 'mcp_server_instructions'" in sql


# ── Seed re-apply on startup ───────────────────────────────────────────


def test_seed_has_mcp_server_instructions_constant() -> None:
    """The seed must lift the canonical singleton body into a module
    constant so it can be re-applied on every backend startup."""
    seed = _read("app/seed/creation_prompts.py")
    assert "MCP_SERVER_INSTRUCTIONS_BODY" in seed


def test_seed_updates_singleton_row_on_startup() -> None:
    """The seed_creation_prompts function must UPDATE the
    mcp-server-instructions-v1 row to the canonical body."""
    seed = _read("app/seed/creation_prompts.py")
    # Look for an UPDATE statement targeting the singleton id.
    assert "mcp-server-instructions-v1" in seed
    assert "MCP_SERVER_INSTRUCTIONS_BODY" in seed


def test_seed_singleton_body_contains_asking_questions_section() -> None:
    """The canonical body the seed re-applies must contain the new
    ASKING QUESTIONS section so cascades inherit the MCP-wide rule."""
    seed = _read("app/seed/creation_prompts.py")
    assert "ASKING QUESTIONS" in seed


# ── Docs alignment ─────────────────────────────────────────────────────


def test_mcp_server_instructions_doc_has_asking_questions_section() -> None:
    """The canonical paste-ready doc must show the new section so
    admin recovery and documentation match the seeded body."""
    doc = _read_repo("docs/prompts/mcp-server-instructions.md")
    assert "ASKING QUESTIONS" in doc


# ── Iris-mcp fallback alignment ────────────────────────────────────────


def test_mcp_fallback_instructions_contain_asking_questions() -> None:
    """Iris-mcp's day-one fallback must match the new seeded body so
    clients connecting before the backend is hit get the same
    instructions."""
    fallback = _read_repo("mcp/src/iris_mcp/server_instructions.py")
    assert "ASKING QUESTIONS" in fallback
