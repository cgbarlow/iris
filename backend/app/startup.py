"""Database startup initialization — runs migrations, seeds, and verifies audit chain."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.audit.service import verify_audit_chain
from app.diagrams.thumbnail import regenerate_all_thumbnails
from app.migrations.m001_roles_users import up as m001_up
from app.migrations.m002_entities_relationships_models import up as m002_up
from app.migrations.m003_audit_log import up as m003_up
from app.migrations.m004_comments_bookmarks import up as m004_up
from app.migrations.m005_search import up as m005_up
from app.migrations.m006_settings import up as m006_up
from app.migrations.m007_thumbnails import up as m007_up
from app.migrations.m008_entity_tags import up as m008_up
from app.migrations.m009_model_tags import up as m009_up
from app.migrations.m010_thumbnail_themes import up as m010_up
from app.migrations.m011_model_hierarchy import up as m011_up
from app.migrations.m012_sets import up as m012_up
from app.migrations.m013_set_thumbnails import up as m013_up
from app.migrations.m014_sets_partial_unique import up as m014_up
from app.migrations.m015_model_relationships import up as m015_up
from app.migrations.m016_naming_rename import up as m016_up
from app.migrations.m017_views import up as m017_up
from app.migrations.m018_package_bookmarks import up as m018_up
from app.migrations.m019_recycle_bin import up as m019_up
from app.migrations.m020_diagram_type_notation_registry import up as m020_up
from app.migrations.m021_edit_locks import up as m021_up
from app.migrations.m022_element_notation import up as m022_up
from app.migrations.m023_new_diagram_types import up as m023_up
from app.migrations.m024_themes import up as m024_up
from app.migrations.m025_diagram_links import up as m025_up
from app.migrations.m026_ai_providers import up as m026_up
from app.migrations.m027_doview_notation import up as m027_up
from app.migrations.m028_ai_creation_prompts import up as m028_up
from app.migrations.m029_sequence_order import up as m029_up
from app.migrations.m030_collections import up as m030_up
from app.migrations.m031_extensions import up as m031_up
from app.migrations.m032_scenia_tables import up as m032_up
from app.migrations.m033_ai_conversations_mode import up as m033_up
from app.migrations.m034_docref_tables import up as m034_up
from app.migrations.m035_packages_fts import up as m035_up
from app.migrations.m036_ai_conversations_nullable_set import up as m036_up
from app.migrations.m037_sets_collections_fts import up as m037_up
from app.migrations.m038_element_bookmarks import up as m038_up
from app.migrations.m039_graph_settings import up as m039_up
from app.migrations.m040_expanded_ai_creation_prompts import up as m040_up
from app.migrations.m041_personal_access_tokens import up as m041_up
from app.migrations.m043_bpmn_notation import up as m043_up
from app.migrations.m044_text_diagram_class import up as m044_up
from app.migrations.m045_images import up as m045_up
from app.migrations.m046_extensions_source import up as m046_up
from app.migrations.m047_scope_system_prompts import up as m047_up
from app.migrations.m048_named_prompts import up as m048_up
from app.migrations.m049_mcp_prompt_column import up as m049_up
from app.migrations.m050_rename_mcp_prompt_to_mcp_system_context import up as m050_up
from app.migrations.m051_response_format_prompts import up as m051_up
from app.migrations.m053_mcp_server_instructions_seed import up as m053_up
from app.migrations.m054_oauth_tables import up as m054_up
from app.migrations.m055_fix_orient_protocol_tool_name import up as m055_up
from app.migrations.m056_fix_scope_context_tool_name import up as m056_up
from app.migrations.m057_fix_stale_auth_recovery import up as m057_up
from app.migrations.m058_cascade_ux_polish import up as m058_up
from app.migrations.m059_mcp_user_question_rule import up as m059_up
from app.migrations.m060_artefacts_table import up as m060_up
from app.migrations.m061_drop_phase1_docx_fallback import up as m061_up
from app.migrations.m062_drop_phase1_move_fallback import up as m062_up
from app.migrations.m063_doview_analysis_creation_format_pointer import up as m063_up
from app.migrations.m064_element_package_membership import up as m064_up
from app.migrations.m065_dynamic_list_diagram_type import up as m065_up
from app.migrations.seed import seed_roles_and_permissions
from app.search.service import rebuild_search_index
from app.seed.creation_prompts import seed_creation_prompts
from app.seed.example_models import seed_example_models
from app.settings.service import seed_defaults

if TYPE_CHECKING:
    from app.database import DatabaseManager


async def initialize_databases(db_manager: DatabaseManager) -> None:
    """Initialize the database(s): connect, run migrations, seed, and verify.

    Called during application startup (lifespan). Branches on db_backend:
    - sqlite (default): runs SQLite migrations, FTS rebuild, thumbnail regeneration
    - supabase: runs PostgreSQL migrations, skips FTS/thumbnails (handled differently)
    """
    # Connect to database(s) — DatabaseManager handles dir creation in SQLite mode.
    await db_manager.connect()

    if db_manager.is_supabase:
        await _initialize_supabase(db_manager)
    else:
        await _initialize_sqlite(db_manager)


async def _initialize_sqlite(db_manager: DatabaseManager) -> None:
    """Run SQLite initialization: migrations, seeds, FTS rebuild, audit verify."""
    # Migrations expect raw aiosqlite.Connection (executescript / SQLite-specific DDL).
    main = db_manager.raw_main_db
    audit = db_manager.raw_audit_db

    # Main database migrations
    await m001_up(main)
    await m002_up(main)
    await m004_up(main)
    await m005_up(main)
    await m006_up(main)
    await m007_up(main)
    await m008_up(main)
    await m009_up(main)
    await m010_up(main)
    await m011_up(main)
    await m012_up(main)
    await m013_up(main)
    await m014_up(main)
    await m015_up(main)
    await m016_up(main)
    await m017_up(main)
    await m018_up(main)
    await m019_up(main)
    await m020_up(main)
    await m021_up(main)
    await m022_up(main)
    await m023_up(main)
    await m024_up(main)
    await m025_up(main)
    await m026_up(main)
    await m027_up(main)
    await m028_up(main)
    await m029_up(main)
    await m030_up(main)
    await m031_up(main)
    await m032_up(main)
    await m033_up(main)
    await m034_up(main)
    await m035_up(main)
    await m036_up(main)
    await m037_up(main)
    await m038_up(main)
    await m039_up(main)
    await m040_up(main)
    await m041_up(main)
    await m043_up(main)
    await m044_up(main)
    await m045_up(main)
    await m046_up(main)
    await m047_up(main)
    await m048_up(main)
    await m049_up(main)
    await m050_up(main)
    await m051_up(main)
    # m052 (pairing_codes) superseded by m054 (drops the table) — ADR-164, v6.0.0.
    await m053_up(main)
    await m054_up(main)
    await m055_up(main)  # issue #115, v6.0.1: fix iris_package_hierarchy → package_hierarchy (server-wide)
    await m056_up(main)  # issue #115, v6.0.2: same fix for per-scope mcp_system_context
    await m057_up(main)  # issue #115 follow-up, v6.0.3: drop stale iris_authenticate refs from singleton body
    await m058_up(main)  # issue #133 Phase 1, v6.1.0: cascade UX polish — three new shared base prompts + DoView/Outcomes Map updates (ADR-176)
    await m059_up(main)  # issue #133 Phase 1, v6.1.0: insert ASKING QUESTIONS section into MCP server-instructions singleton (ADR-177)
    await m060_up(main)  # issue #133 Phase 2, v6.2.0: artefacts table for rendered md/docx/pdf (ADR-179)
    await m061_up(main)  # issue #133 Phase 2, v6.2.0: drop Phase-1 docx/pdf fallback from cascade destination prompt (ADR-179)
    await m062_up(main)  # issue #133 Phase 3, v6.3.0: drop Phase-1 cross-set move fallback (ADR-178)
    await m063_up(main)  # issue #133 Phase 1 UAT defect, v6.6.2: backstop creation_format pointer to response_format for (markdown, doview_analysis)
    await m064_up(main)  # issue #149, v6.7.0: elements.package_id column (ADR-184)
    await m065_up(main)  # issue #147, v6.7.0: dynamic_list diagram_type (ADR-186)

    # Service-layer seeds — receive DatabasePort (SqliteAdapter wrapping main)
    port = db_manager.main_db
    from app.views.service import seed_default_views
    await seed_default_views(port)
    from app.themes.service import seed_default_themes
    await seed_default_themes(port)
    from app.graph.service import seed_graph_settings_defaults
    await seed_graph_settings_defaults(port)

    # Rebuild FTS search index from existing data
    await rebuild_search_index(port)

    # Regenerate PNG thumbnails for all models
    await regenerate_all_thumbnails(port)

    # Seed roles, permissions, settings, example models
    await seed_roles_and_permissions(port)
    await seed_defaults(port)
    await seed_example_models(port)
    # Bring AI creation prompts to the latest canonical content on every start
    # (ADR-132): admin edits are overwritten, matching the pattern used for
    # DoView-era prompts.
    await seed_creation_prompts(port)

    # Audit database migration and chain verification
    await m003_up(audit)
    audit_port = db_manager.audit_db
    is_valid, entries_checked = await verify_audit_chain(audit_port)
    if not is_valid:
        msg = (
            f"Audit chain verification failed at entry {entries_checked}. "
            "Database integrity may be compromised."
        )
        raise RuntimeError(msg)


async def _initialize_supabase(db_manager: DatabaseManager) -> None:
    """Run Supabase/PostgreSQL initialization: run idempotent migrations, seed core data.

    FTS rebuild and thumbnail generation are skipped:
    - FTS uses PostgreSQL tsvector triggers (auto-updated on INSERT/UPDATE)
    - cairosvg thumbnail generation may not be available in Netlify Function runtime
    """
    # Migrations are run externally via psql (scripts/supabase-migrate.sh or SQL Editor).
    # asyncpg cannot execute dollar-quoted SQL ($$) used in trigger/function definitions.
    # See docs/deployment-render-supabase.md Step 2.

    # Seed roles, permissions, settings, themes, views via DatabasePort (SupabaseAdapter).
    from app.themes.service import seed_default_themes  # noqa: PLC0415
    from app.views.service import seed_default_views  # noqa: PLC0415

    port = db_manager.main_db
    await seed_roles_and_permissions(port)
    await seed_defaults(port)
    await seed_default_themes(port)
    await seed_default_views(port)
    # ADR-117 v5.7.2 amendment: ensure the `graph_settings` table
    # exists on Supabase deployments that may not have run the m039
    # SQL migration via supabase-migrate.sh. Idempotent — does nothing
    # if the table is already there. Without this, the seed below
    # would log-and-skip (v5.7.1 made it defensive), so no row would
    # ever be inserted and admin "Save as default" PUTs would fail.
    await port.execute(
        "CREATE TABLE IF NOT EXISTS graph_settings ("
        "  scope_type TEXT NOT NULL CHECK(scope_type IN ('global','collection','set')),"
        "  scope_id TEXT NOT NULL,"
        "  settings_json TEXT NOT NULL,"
        "  updated_at TIMESTAMPTZ,"
        "  updated_by TEXT,"
        "  PRIMARY KEY (scope_type, scope_id)"
        ")"
    )
    # v5.8.1: align graph_settings with the ADR-095 deny-all RLS posture.
    # PostgreSQL's ENABLE ROW LEVEL SECURITY is idempotent — safe on every
    # startup. Fixes a Supabase advisor warning where graph_settings was the
    # only post-m030 table without RLS.
    await port.execute("ALTER TABLE graph_settings ENABLE ROW LEVEL SECURITY")
    await port.commit()
    # ADR-117 v5.7.1 amendment: ensure the `__global__` row exists on
    # Supabase startup (the SQLite path already does this on line ~139).
    from app.graph.service import seed_graph_settings_defaults  # noqa: PLC0415
    await seed_graph_settings_defaults(port)
    # Bring AI creation prompts to the latest canonical content (ADR-132).
    # The m041 Supabase migration seeds the initial rows externally via psql;
    # this call keeps prompt_text fresh on each app restart without a new
    # migration per tweak.
    try:
        await seed_creation_prompts(port)
    except Exception as exc:  # noqa: BLE001
        # Soft failure — don't block startup if the table isn't ready yet.
        print(f"[AI_CREATION] seed_creation_prompts skipped on Supabase: {exc}", flush=True)

    # Run lightweight schema patches that don't require dollar-quoting (safe for asyncpg).
    # m031: add mode and thread_id columns to ai_conversations if missing.
    await port.execute(
        "ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS mode TEXT DEFAULT 'discuss'"
    )
    await port.execute(
        "ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS thread_id TEXT"
    )
    await port.commit()

    # m032: add sequence_order column to diagrams and packages if missing.
    await port.execute(
        "ALTER TABLE diagrams ADD COLUMN IF NOT EXISTS sequence_order INTEGER NOT NULL DEFAULT 0"
    )
    await port.execute(
        "ALTER TABLE packages ADD COLUMN IF NOT EXISTS sequence_order INTEGER NOT NULL DEFAULT 0"
    )
    await port.commit()

    # m036: Fix timestamp columns TEXT → TIMESTAMPTZ.
    # The _convert_params adapter converts ISO strings to datetime objects, which
    # asyncpg rejects for TEXT columns. Alter to TIMESTAMPTZ so datetimes are accepted.
    for _table, _col in [
        ("scenia_timeline_settings", "updated_at"),
        ("scenia_versions", "created_at"),
        ("extensions", "installed_at"),
        ("extensions", "updated_at"),
    ]:
        try:
            # Fix any underscore-separated timestamps from legacy seed data
            await port.execute(
                f"UPDATE {_table} SET {_col} = REPLACE({_col}::text, '_', 'T')"  # noqa: S608
            )
            await port.execute(
                f"ALTER TABLE {_table} ALTER COLUMN {_col} TYPE TIMESTAMPTZ "
                f"USING {_col}::TIMESTAMPTZ"
            )
        except Exception:
            pass  # Table may not exist yet (scenia extension not installed)
    await port.commit()

    # Sync profiles → users table so FK constraints (elements.created_by, etc.) are satisfied.
    # The `users` table is the SQLite-era user store; in Supabase mode it's empty but still
    # referenced by FKs. Mirror each profile into `users` so CRUD operations succeed.
    await port.execute(
        "INSERT INTO users (id, username, password_hash, role, is_active) "
        "SELECT id::text, username, 'supabase-managed', role, is_active "
        "FROM profiles "
        "WHERE id::text NOT IN (SELECT id FROM users)"
    )
    await port.commit()
