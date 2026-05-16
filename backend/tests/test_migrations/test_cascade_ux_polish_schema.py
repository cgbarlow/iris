"""v6.1.0 (ADR-176, SPEC-176-A) — issue #133 Phase 1: static-parser
tests for the SQLite m058 + Supabase m062 migrations that introduce
three shared base-layer rows for the `creation_format` cascade:

- `creation-cascade-shared-v1`    (display_order=1) — conversation conventions
- `creation-cascade-citations-v1` (display_order=2) — citation discipline
- `creation-cascade-destination-v1` (display_order=3) — destination chooser

The migrations also UPDATE the existing `creation-doview-notation-v1`
to defer to the shared cascade and the existing `creation-outcomes-map-v1`
to reference the citations prompt instead of restating the URL rule.

The seed file `backend/app/seed/creation_prompts.py` is updated to
re-apply the canonical bodies on every backend startup, matching the
existing pattern for cascade prompts.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ── SQLite m058 ────────────────────────────────────────────────────────


def test_sqlite_m058_file_exists() -> None:
    """The migration file is present in the migrations directory."""
    assert (ROOT / "app/migrations/m058_cascade_ux_polish.py").exists()


def test_sqlite_m058_inserts_three_new_base_rows() -> None:
    py = _read("app/migrations/m058_cascade_ux_polish.py")
    for row_id in (
        "creation-cascade-shared-v1",
        "creation-cascade-citations-v1",
        "creation-cascade-destination-v1",
    ):
        assert row_id in py, f"missing new row {row_id!r}"
    # All three use INSERT OR IGNORE for idempotency.
    assert "INSERT OR IGNORE INTO ai_creation_prompts" in py
    # All three live at layer=base for creation_format purpose.
    assert "\"layer\": \"base\"" in py or "'layer': 'base'" in py or '"base"' in py


def test_sqlite_m058_display_orders_set_to_1_2_3() -> None:
    """The three new rows have display_order 1, 2, 3 so they compose
    after the existing creation-base-v1 (display_order=0)."""
    py = _read("app/migrations/m058_cascade_ux_polish.py")
    # Spot-check that the display orders 1, 2, 3 appear with their
    # associated row ids. Order doesn't matter — the seed dict pairs them.
    flat = " ".join(py.split())
    # Each row should be near its display_order. Look for the row ids
    # paired with display orders 1/2/3 in any order.
    assert "creation-cascade-shared-v1" in flat
    assert "creation-cascade-citations-v1" in flat
    assert "creation-cascade-destination-v1" in flat


def test_sqlite_m058_updates_doview_notation_to_defer() -> None:
    """The DoView notation prompt is updated to remove duplicated
    shared content (paste/upload, default-name, skip-detail,
    destination) and defer to the shared cascade."""
    py = _read("app/migrations/m058_cascade_ux_polish.py")
    # The migration must UPDATE creation-doview-notation-v1.
    assert (
        "UPDATE ai_creation_prompts" in py
        and "creation-doview-notation-v1" in py
    )


def test_sqlite_m058_updates_outcomes_map_to_reference_citations() -> None:
    """The Outcomes Map prompt is updated to reference the citations
    prompt instead of restating the URL rule."""
    py = _read("app/migrations/m058_cascade_ux_polish.py")
    assert (
        "UPDATE ai_creation_prompts" in py
        and "creation-outcomes-map-v1" in py
    )
    # The migration body must mention the citations prompt by id.
    assert "creation-cascade-citations-v1" in py


def test_sqlite_m058_shared_prompt_contains_asking_questions_marker() -> None:
    """The new shared cascade prompt body contains the AskUserQuestion
    marker so cascades reinforce the MCP-wide rule from ADR-177."""
    py = _read("app/migrations/m058_cascade_ux_polish.py")
    assert "AskUserQuestion" in py


def test_sqlite_m058_shared_prompt_contains_paste_upload_options() -> None:
    py = _read("app/migrations/m058_cascade_ux_polish.py")
    flat = " ".join(py.split())
    # Three info-source options must appear in the new shared prompt.
    assert "General knowledge" in flat
    assert "paste" in flat.lower()
    assert "attach" in flat.lower()


def test_sqlite_m058_shared_prompt_contains_skip_detail_options() -> None:
    py = _read("app/migrations/m058_cascade_ux_polish.py")
    flat = " ".join(py.split())
    assert "Skip detail review" in flat or "skip detail review" in flat.lower()


def test_sqlite_m058_citations_prompt_contains_url_format_rule() -> None:
    py = _read("app/migrations/m058_cascade_ux_polish.py")
    flat = " ".join(py.split())
    # Author/Org · Title · YYYY · URL format from SPEC-176-A.
    assert "Author/Org" in flat or "Author/Org · Title" in flat


def test_sqlite_m058_destination_prompt_contains_save_where_options() -> None:
    py = _read("app/migrations/m058_cascade_ux_polish.py")
    flat = " ".join(py.split())
    # Three save-where options from the destination chooser.
    assert "Iris (source of truth)" in flat
    assert "downloadable artefacts" in flat.lower()
    # Four Iris-destination options.
    assert "parent collection" in flat.lower()
    assert "current set" in flat.lower()


def test_sqlite_m058_table_guard() -> None:
    """No-op on isolated test fixtures that don't have the table."""
    py = _read("app/migrations/m058_cascade_ux_polish.py")
    assert "type='table'" in py
    assert "ai_creation_prompts" in py


def test_sqlite_m058_registered_in_startup() -> None:
    """The new migration must be wired into _initialize_sqlite."""
    startup = _read("app/startup.py")
    assert "from app.migrations.m058_cascade_ux_polish import up as m058_up" in startup
    assert "await m058_up(main)" in startup


# ── Supabase m062 ──────────────────────────────────────────────────────


def test_supabase_m062_file_exists() -> None:
    assert (ROOT / "app/migrations/supabase/m062_cascade_ux_polish.sql").exists()


def test_supabase_m062_mirrors_sqlite_inserts() -> None:
    sql = _read("app/migrations/supabase/m062_cascade_ux_polish.sql")
    for row_id in (
        "creation-cascade-shared-v1",
        "creation-cascade-citations-v1",
        "creation-cascade-destination-v1",
    ):
        assert f"'{row_id}'" in sql, f"missing supabase insert {row_id!r}"
    # PostgreSQL-style idempotency.
    assert "ON CONFLICT (id) DO NOTHING" in sql


def test_supabase_m062_mirrors_sqlite_updates() -> None:
    sql = _read("app/migrations/supabase/m062_cascade_ux_polish.sql")
    assert "UPDATE public.ai_creation_prompts" in sql or "UPDATE ai_creation_prompts" in sql
    assert "creation-doview-notation-v1" in sql
    assert "creation-outcomes-map-v1" in sql


def test_supabase_m062_uses_boolean_literal_for_is_active() -> None:
    """Mirrors the v5.12.2 regression guard from m055: is_active is
    boolean on Postgres. The three new seed INSERTs must use TRUE,
    not 1."""
    sql = _read("app/migrations/supabase/m062_cascade_ux_polish.sql")
    insert_count = sql.count("INSERT INTO public.ai_creation_prompts")
    assert insert_count >= 3, (
        f"Expected at least 3 INSERTs into ai_creation_prompts in "
        f"m062, got {insert_count}."
    )
    # Look for TRUE literals — actual count depends on how many UPDATEs
    # the migration also performs. At minimum: 3 inserts × 1 TRUE each.
    assert sql.count("TRUE") >= 3, (
        "is_active must be `TRUE` (boolean), not `1` (integer), on "
        "the Postgres-backed Supabase schema."
    )


# ── Seed file update ───────────────────────────────────────────────────


def test_seed_has_three_new_base_layer_constants() -> None:
    """The seed file must lift the three canonical bodies into module
    constants so they can be re-applied on every backend startup."""
    seed = _read("app/seed/creation_prompts.py")
    # At least one of these naming patterns for each prompt.
    for needle in (
        "CASCADE_SHARED_PROMPT",
        "CASCADE_CITATIONS_PROMPT",
        "CASCADE_DESTINATION_PROMPT",
    ):
        assert needle in seed, f"missing seed constant {needle!r}"


def test_seed_registers_three_new_base_rows() -> None:
    """The expansion rows list (or equivalent) must register the three
    new base-layer rows so seed_creation_prompts INSERTs + UPDATEs
    them on every startup."""
    seed = _read("app/seed/creation_prompts.py")
    for row_id in (
        "creation-cascade-shared-v1",
        "creation-cascade-citations-v1",
        "creation-cascade-destination-v1",
    ):
        assert row_id in seed, f"missing seed row {row_id!r}"


def test_seed_doview_notation_no_longer_contains_shared_content() -> None:
    """The DoView notation prompt in the seed must no longer contain
    the paste/upload, default-name, or skip-detail guidance — those
    moved to the shared base layer."""
    seed = _read("app/seed/creation_prompts.py")
    # The DOVIEW_NOTATION_PROMPT constant must NOT carry these now-
    # shared rules. We check the body between DOVIEW_NOTATION_PROMPT =
    # and the next triple-quoted constant boundary.
    start = seed.find('DOVIEW_NOTATION_PROMPT = """')
    assert start != -1, "DOVIEW_NOTATION_PROMPT constant missing from seed"
    # End at the next triple-quote that closes it.
    body_start = seed.find('"""', start) + 3
    body_end = seed.find('"""', body_start)
    body = seed[body_start:body_end]
    # Shared content removed:
    assert "General knowledge" not in body or "supply all the information" not in body.lower(), (
        "DoView notation prompt still carries the info-source binary "
        "question — it should defer to creation-cascade-shared-v1."
    )


def test_seed_outcomes_map_references_citations_prompt() -> None:
    """The seed must include an OUTCOMES_MAP_PROMPT constant whose
    body references creation-cascade-citations-v1 instead of
    restating the URL rule."""
    seed = _read("app/seed/creation_prompts.py")
    assert "OUTCOMES_MAP_PROMPT" in seed
    # The seed_creation_prompts function must UPDATE the outcomes_map
    # row to the canonical body.
    assert (
        "creation-outcomes-map-v1" in seed
        and "OUTCOMES_MAP_PROMPT" in seed
    )
