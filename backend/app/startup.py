"""Database startup initialization — runs migrations, seeds, and verifies audit chain."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.audit.service import verify_audit_chain
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
from app.migrations.seed import seed_roles_and_permissions
from app.diagrams.thumbnail import regenerate_all_thumbnails
from app.search.service import rebuild_search_index
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

    # Service-layer seeds — receive DatabasePort (SqliteAdapter wrapping main)
    port = db_manager.main_db
    from app.views.service import seed_default_views
    await seed_default_views(port)
    from app.themes.service import seed_default_themes
    await seed_default_themes(port)

    # Rebuild FTS search index from existing data
    await rebuild_search_index(port)

    # Regenerate PNG thumbnails for all models
    await regenerate_all_thumbnails(port)

    # Seed roles, permissions, settings, example models
    await seed_roles_and_permissions(port)
    await seed_defaults(port)
    await seed_example_models(port)

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
