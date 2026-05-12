"""v5.12.0 (ADR-157, SPEC-157-A): static-parser tests asserting that
SQLite m051 and Supabase m055 add the `purpose` column to
`ai_creation_prompts`, register the `markdown` notation and
`doview_analysis` diagram_type, and seed three response_format
prompt rows (base / notation / diagram_type layers).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ── SQLite m051 ─────────────────────────────────────────────────────────


def test_sqlite_m051_adds_purpose_column() -> None:
    py = _read("app/migrations/m051_response_format_prompts.py")
    assert "ADD COLUMN purpose TEXT" in py
    assert "DEFAULT 'creation_format'" in py


def test_sqlite_m051_backfills_existing_rows() -> None:
    py = _read("app/migrations/m051_response_format_prompts.py")
    assert "UPDATE ai_creation_prompts SET purpose = 'creation_format'" in py


def test_sqlite_m051_registers_markdown_notation() -> None:
    py = _read("app/migrations/m051_response_format_prompts.py")
    assert "INSERT OR IGNORE INTO notations" in py
    assert "\"markdown\"" in py
    assert "\"Markdown\"" in py


def test_sqlite_m051_registers_doview_analysis_diagram_type() -> None:
    py = _read("app/migrations/m051_response_format_prompts.py")
    assert "INSERT OR IGNORE INTO diagram_types" in py
    assert "\"doview_analysis\"" in py
    assert "\"DoView Analysis\"" in py


def test_sqlite_m051_maps_doview_analysis_to_markdown() -> None:
    py = _read("app/migrations/m051_response_format_prompts.py")
    assert "INSERT OR IGNORE INTO diagram_type_notations" in py
    assert "(\"doview_analysis\", \"markdown\", 1)" in py


def test_sqlite_m051_seeds_three_response_format_layers() -> None:
    py = _read("app/migrations/m051_response_format_prompts.py")
    for prompt_id in (
        "response-format-base-v1",
        "response-format-doview-notation-v1",
        "response-format-doview-analysis-v1",
    ):
        assert prompt_id in py, f"missing seed prompt {prompt_id!r}"
    # Each layer accounted for.
    assert "\"purpose\": \"response_format\"" in py
    assert "\"layer\": \"base\"" in py
    assert "\"layer\": \"notation\"" in py
    assert "\"layer\": \"diagram_type\"" in py


def test_sqlite_m051_seeds_doview_rules_content() -> None:
    py = _read("app/migrations/m051_response_format_prompts.py")
    # Spot-check that key Prompt-C rules are encoded in the seeds.
    # Use whitespace-tolerant checks since the seed bodies are line-wrapped.
    flat = " ".join(py.split())
    assert "Outcomes theory points out that" in flat
    assert "DoView is the practical applied form" in flat
    assert "outcomes system" in flat
    assert "I have prepared a summary response" in flat
    assert "doviewplanning.org" in flat


# ── Supabase m055 ───────────────────────────────────────────────────────


def test_supabase_m055_adds_purpose_column_idempotently() -> None:
    sql = _read("app/migrations/supabase/m055_response_format_prompts.sql")
    assert "ADD COLUMN IF NOT EXISTS purpose TEXT" in sql
    assert "DEFAULT 'creation_format'" in sql


def test_supabase_m055_registers_markdown_and_doview_analysis() -> None:
    sql = _read("app/migrations/supabase/m055_response_format_prompts.sql")
    assert "INSERT INTO public.notations" in sql
    assert "'markdown'" in sql
    assert "INSERT INTO public.diagram_types" in sql
    assert "'doview_analysis'" in sql
    assert "ON CONFLICT (id) DO NOTHING" in sql


def test_supabase_m055_uses_boolean_literal_for_is_default() -> None:
    """v5.12.1 regression: `diagram_type_notations.is_default` is boolean
    on Postgres (Supabase). Using `1` (integer, SQLite convention)
    triggers `column "is_default" is of type boolean but expression is
    of type integer`. The Supabase migration must use TRUE/FALSE."""
    sql = _read("app/migrations/supabase/m055_response_format_prompts.sql")
    # The doview_analysis ↔ markdown mapping must use a boolean literal.
    assert "VALUES ('doview_analysis', 'markdown', TRUE)" in sql, (
        "is_default must be `TRUE` (boolean), not `1` (integer), "
        "on the Postgres-backed Supabase schema."
    )


def test_supabase_m055_seeds_three_response_format_rows() -> None:
    sql = _read("app/migrations/supabase/m055_response_format_prompts.sql")
    for prompt_id in (
        "response-format-base-v1",
        "response-format-doview-notation-v1",
        "response-format-doview-analysis-v1",
    ):
        assert prompt_id in sql, f"missing supabase seed {prompt_id!r}"
    assert sql.count("'response_format'") >= 3
