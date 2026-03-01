"""Database startup initialization — runs migrations, seeds, and verifies audit chain."""

from __future__ import annotations

import os
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
from app.migrations.seed import seed_roles_and_permissions
from app.models_crud.thumbnail import regenerate_all_thumbnails
from app.search.service import rebuild_search_index
from app.seed.example_models import seed_example_models
from app.settings.service import seed_defaults

if TYPE_CHECKING:
    from app.database import DatabaseManager


async def initialize_databases(db_manager: DatabaseManager) -> None:
    """Initialize both databases: create dirs, run migrations, seed, verify.

    Called during application startup (lifespan).
    """
    # 1. Ensure data directory exists
    data_dir = os.path.dirname(db_manager.config.main_db_path)
    os.makedirs(data_dir, exist_ok=True)

    # 2. Connect to both databases
    await db_manager.connect()

    # 3. Run main database migrations
    await m001_up(db_manager.main_db)
    await m002_up(db_manager.main_db)
    await m004_up(db_manager.main_db)
    await m005_up(db_manager.main_db)
    await m006_up(db_manager.main_db)
    await m007_up(db_manager.main_db)
    await m008_up(db_manager.main_db)
    await m009_up(db_manager.main_db)
    await m010_up(db_manager.main_db)

    # 3b. Rebuild FTS search index from existing data
    await rebuild_search_index(db_manager.main_db)

    # 3c. Regenerate PNG thumbnails for all models
    await regenerate_all_thumbnails(db_manager.main_db)

    # 4. Seed roles and permissions
    await seed_roles_and_permissions(db_manager.main_db)

    # 4b. Seed default settings
    await seed_defaults(db_manager.main_db)

    # 4c. Seed example models (Iris architecture demo)
    await seed_example_models(db_manager.main_db)

    # 5. Run audit database migration
    await m003_up(db_manager.audit_db)

    # 6. Verify audit chain integrity
    is_valid, entries_checked = await verify_audit_chain(db_manager.audit_db)
    if not is_valid:
        msg = (
            f"Audit chain verification failed at entry {entries_checked}. "
            "Database integrity may be compromised."
        )
        raise RuntimeError(msg)
