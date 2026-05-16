"""v6.6.2: static-parser tests for SQLite m063 + Supabase m067 — the
backstop creation_format pointer for (markdown, doview_analysis)
that fixes the Phase 1 UAT regression where cascade-created
doview_analyses didn't follow the response_format output structure.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ── SQLite m063 ────────────────────────────────────────────────────────


def test_sqlite_m063_file_exists() -> None:
    assert (ROOT / "app/migrations/m063_doview_analysis_creation_format_pointer.py").exists()


def test_sqlite_m063_inserts_pointer_row() -> None:
    py = _read("app/migrations/m063_doview_analysis_creation_format_pointer.py")
    assert "creation-format-doview-analysis-pointer-v1" in py
    assert "INSERT OR IGNORE INTO ai_creation_prompts" in py


def test_sqlite_m063_pointer_is_diagram_type_layer() -> None:
    py = _read("app/migrations/m063_doview_analysis_creation_format_pointer.py")
    # Must be scoped to (creation_format, diagram_type, doview_analysis)
    # so it only composes when creating a doview_analysis.
    assert '"purpose": "creation_format"' in py
    assert '"layer": "diagram_type"' in py
    assert '"diagram_type": "doview_analysis"' in py


def test_sqlite_m063_pointer_references_response_format() -> None:
    py = _read("app/migrations/m063_doview_analysis_creation_format_pointer.py")
    # The body must instruct the model to fetch the response_format
    # cascade — otherwise the pointer is useless.
    flat = " ".join(py.split())
    assert "response_format" in flat
    assert "get_response_prompt" in flat
    assert "purpose='response_format'" in flat or "purpose=\"response_format\"" in flat


def test_sqlite_m063_table_guard() -> None:
    py = _read("app/migrations/m063_doview_analysis_creation_format_pointer.py")
    assert "type='table'" in py


def test_sqlite_m063_registered_in_startup() -> None:
    startup = _read("app/startup.py")
    assert (
        "from app.migrations.m063_doview_analysis_creation_format_pointer "
        "import up as m063_up"
    ) in startup
    assert "await m063_up(main)" in startup


# ── Supabase m067 ──────────────────────────────────────────────────────


def test_supabase_m067_file_exists() -> None:
    assert (ROOT / "app/migrations/supabase/m067_doview_analysis_creation_format_pointer.sql").exists()


def test_supabase_m067_mirrors_sqlite() -> None:
    sql = _read("app/migrations/supabase/m067_doview_analysis_creation_format_pointer.sql")
    assert "creation-format-doview-analysis-pointer-v1" in sql
    assert "'creation_format'" in sql
    assert "'diagram_type'" in sql
    assert "'doview_analysis'" in sql
    assert "get_response_prompt" in sql
    assert "purpose='response_format'" in sql
    assert "ON CONFLICT (id) DO NOTHING" in sql


def test_supabase_m067_is_active_uses_true_literal() -> None:
    """Boolean column on PostgreSQL — must use TRUE, not 1
    (v5.12.2 regression guard pattern)."""
    sql = _read("app/migrations/supabase/m067_doview_analysis_creation_format_pointer.sql")
    assert "TRUE" in sql


# ── Seed canonical body ────────────────────────────────────────────────


def test_seed_has_doview_analysis_pointer_constant() -> None:
    seed = _read("app/seed/creation_prompts.py")
    assert "DOVIEW_ANALYSIS_CREATION_FORMAT_POINTER" in seed


def test_seed_registers_pointer_row_in_expansion() -> None:
    seed = _read("app/seed/creation_prompts.py")
    # The expansion-rows list must include the pointer so it's
    # re-applied on every backend startup (matches the existing
    # ship-latest pattern for cascade prompts).
    assert "creation-format-doview-analysis-pointer-v1" in seed


# ── tools.py preamble update ───────────────────────────────────────────


REPO_ROOT = ROOT.parent


def test_creation_flow_preamble_mentions_response_format_for_markdown() -> None:
    """The companion fix in mcp/src/iris_mcp/tools.py adds explicit
    instructions in _CREATION_FLOW_PREAMBLE step 2a for the model to
    fetch and apply response_format rules when creating markdown
    content-bearing diagrams. Without this, the cascade-create path
    silently produces unstructured markdown for doview_analysis (the
    bug this fix closes)."""
    tools_py = (REPO_ROOT / "mcp/src/iris_mcp/tools.py").read_text(encoding="utf-8")
    flat = " ".join(tools_py.split())
    assert "CRITICAL for content-bearing markdown diagrams" in flat
    assert "purpose='response_format'" in flat
    assert "doview_analysis" in flat
